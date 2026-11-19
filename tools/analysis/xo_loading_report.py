"""Crossover-region loading diagnostics for stored designs (REPORT-ONLY; never a score term).

Gate A of the 2026-11-19 senior direction
(``scratch/fable_architecture/xo_loading_gateA_2026-11-19/REPORT.md``). Per design dir
(``.../designs/<hash>`` holding ``response.npz``), at every STORED frequency:

* complex throat impedance ``z`` (specific, /rho c). The BEM stores exp(-i w t), so mass-like
  loading has Im z < 0; ``im_z_eng`` = -Im z is the engineering-convention reactance (+ = mass-like);
* ``gamma`` = |(z-1)/(z+1)|, a single-plane-wave diagnostic only (modal fields invalidate it);
* levels in BOTH source conventions. The solver drives unit normal ACCELERATION
  (``meta.spl_reference``); every stored dB (``on_axis_db``, ``spl_*``) is per unit acceleration.
  ``*_vel`` = ``*_acc`` + 20 log10(w) is per unit throat VELOCITY. Comparing an LF level against a HF
  level in ``_acc`` units adds 20 log10(f_hf / f_lf) (7.7 dB from 828 Hz to 2 kHz): the 2026-11-19
  audit's "+10 dB crossover hump" was exactly that mistake;
* ``energy_ratio`` = balloon-integrated radiated power / (1/2 rho c Re z S |v|^2). It is ~1 when z,
  area, balloon and normalisation agree. Away from 1, suspect the data, not the acoustics;
* the v7/v10 ``load`` pieces (LFP20, min Re z over [F_X, loaded_hi], raw penalty), recomputed with
  ``scalar_v7`` defaults so they match the scorer;
* a voltage-driven response through ``hornlab_search.driver.compression.drive`` for each driver given,
  optionally through an ideal Butterworth voltage high pass at F_X.

  Without ``--driver``, a 32-member BRACKET of 1.4"-exit compression drivers is used, labelled
  [inferred]: no 1.4" pro driver checked publishes Mmd, Sd and fs (HF1440, 18 Sound ND1460A/NSD1424BTN/
  NSD1460N, RCF ND950 1.4, Celestion CDX14-3040, Beyma CD-1114Fe; see the Gate A report). Absolute
  levels from the bracket are not meaningful. Horn-vs-horn differences on one driver are.

Zero solver calls; reads only; writes ``--out`` (refused when it exists and is not empty).

    python tools/analysis/xo_loading_report.py --out runs/analysis/<name> \
        fold=runs/<run>/designs/<hash> rosse=runs/<run>/designs/<hash> ...
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.constants import C_AIR, RHO_AIR  # noqa: E402

#: [inferred] 1.4"-exit compression-driver bracket (2^5 = 32 members). Bl 12-18 T m covers the two
#: published 1.4" values found (18 Sound ND1460A 13.5, RCF ND950 1.4 17.6).
BRACKET = {"sd_cm2": (30.0, 45.0), "mmd_g": (1.5, 3.0), "bl_tm": (12.0, 18.0),
           "fs_hz": (450.0, 700.0), "front_chamber_cm3": (0.0, 3.0)}
BRACKET_FIXED = {"kind": "compression", "re_ohm": 6.8, "le_mh": 0.05, "qms": 3.0}


# ----------------------------------------------------------------------------- pure helpers

def velocity_db(acc_db, freqs_hz) -> np.ndarray:
    """Level per unit throat acceleration -> per unit throat velocity (|a| = w |v|)."""
    return np.asarray(acc_db, float) + 20.0 * np.log10(2.0 * np.pi * np.asarray(freqs_hz, float))


def reflection_mag(z) -> np.ndarray:
    """|(z-1)/(z+1)| for normalised specific impedance z. Same in either time convention."""
    z = np.asarray(z, complex)
    return np.abs((z - 1.0) / (z + 1.0))


def rel_db(freqs_hz, y, at_hz: float, ref_hz: float) -> float:
    """y(at) - y(ref), each linear in log f between stored samples (NaN outside the grid)."""
    f = np.asarray(freqs_hz, float)
    y = np.asarray(y, float)
    if not (f.min() <= at_hz <= f.max() and f.min() <= ref_hz <= f.max()):
        return float("nan")
    lf = np.log(f)
    return float(np.interp(math.log(at_hz), lf, y) - np.interp(math.log(ref_hz), lf, y))


def detrended_residual(freqs_hz, y, lo_hz: float, hi_hz: float) -> tuple[float, float]:
    """(max, std) of y minus its least-squares line in log2 f over [lo, hi]. NaN with < 3 samples."""
    f = np.asarray(freqs_hz, float)
    y = np.asarray(y, float)
    m = (f >= lo_hz) & (f <= hi_hz) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan"), float("nan")
    x = np.log2(f[m])
    res = y[m] - np.polyval(np.polyfit(x, y[m], 1), x)
    return float(res.max()), float(res.std())


def balloon_power_per_accel(resp) -> np.ndarray:
    """Radiated power (W) per unit throat acceleration amplitude, full sphere.

    Theta-phi balloon grid (theta from +Z), sin(theta) quadrature normalised to 4 pi, intensity
    |p|^2 / (2 rho c) at ``meta.distance_m`` (peak-amplitude phasors, as the solver stores them)."""
    dirs = np.asarray(resp.balloon_dirs, float)
    p = np.asarray(resp.p_balloon)
    w = np.sin(np.arccos(np.clip(dirs[:, 2], -1.0, 1.0)))
    w = w * (4.0 * np.pi / w.sum())
    r = float(resp.meta["distance_m"])
    return r ** 2 * (np.abs(p) ** 2 @ w) / (2.0 * RHO_AIR * C_AIR)


def input_power_per_accel(resp) -> np.ndarray:
    """1/2 rho c Re(z) S |v|^2 with |v| = 1/w (unit acceleration), S = full-model throat area."""
    from hornlab_search.metrics.loudness import throat_area_m2
    f = np.asarray(resp.freqs_hz, float)
    om = 2.0 * np.pi * f
    return 0.5 * RHO_AIR * C_AIR * np.real(np.asarray(resp.z_throat, complex)) * throat_area_m2(resp) / om ** 2


def load_pieces(freqs_hz, re_z, fx_hz: float, loaded_hi_hz: float) -> dict:
    """The v7/v10 ``load`` raw penalty and its parts, with the scorer's own defaults."""
    from hornlab_search.objective.scalar_v7 import V7Params, _first_crossing_hz
    prm = V7Params(tolerances={})                # only the load-term defaults are read
    f = np.asarray(freqs_hz, float)
    z = np.asarray(re_z, float)
    m = np.isfinite(z) & (f >= fx_hz) & (f <= loaded_hi_hz)
    lfp20 = _first_crossing_hz(f, z, prm.lfp_re_z)
    rez_min = float(z[m].min()) if m.any() else float("nan")
    lfp_pen = max(0.0, math.log2(lfp20 * prm.lfp_crossover_ratio / fx_hz)) if lfp20 else float("nan")
    rez_pen = max(0.0, prm.loaded_re_z - rez_min) if m.any() else float("nan")
    return {"lfp20_hz": lfp20, "rez_min": rez_min,
            "f_rez_min_hz": float(f[m][np.argmin(z[m])]) if m.any() else float("nan"),
            "lfp_pen": lfp_pen, "rez_pen": rez_pen, "load_raw": lfp_pen + rez_pen}


def butterworth_hp(freqs_hz, fc_hz: float, order: int = 2) -> np.ndarray:
    """Ideal Butterworth high-pass magnitude (voltage transfer, no impedance interaction)."""
    x = np.asarray(freqs_hz, float) / fc_hz
    return x ** order / np.sqrt(1.0 + x ** (2 * order))


def bracket_drivers() -> list[dict]:
    keys = list(BRACKET)
    return [dict(BRACKET_FIXED, name="bracket[" + ",".join(f"{k}={v:g}" for k, v in zip(keys, c)) + "]",
                 **dict(zip(keys, c))) for c in itertools.product(*BRACKET.values())]


# ----------------------------------------------------------------------------- per design

def diagnose(resp, *, fx_hz: float = 700.0, ref_hz: float = 2000.0, loaded_hi_hz: float = 5600.0,
             band=(600.0, 3000.0), probe_hz=(643.0, 828.0, 1065.0), drivers=None,
             hp_order: int = 2) -> dict:
    """Per-frequency arrays and a summary for one stored Response (see module docstring)."""
    from hornlab_search.driver.compression import CompressionDriver, drive
    f = np.asarray(resp.freqs_hz, float)
    z = np.asarray(resp.z_throat, complex)
    ax = resp.axis_index
    on_acc = 20.0 * np.log10(np.abs(np.asarray(resp.p_h)[:, ax]) / 20e-6)
    p_rad = balloon_power_per_accel(resp)
    pwl_acc = 10.0 * np.log10(p_rad / 1e-12)
    per = {"freq_hz": f, "re_z": z.real, "im_z_eng": -z.imag, "gamma": reflection_mag(z),
           "on_axis_acc_db": on_acc, "on_axis_vel_db": velocity_db(on_acc, f),
           "power_acc_db": pwl_acc, "power_vel_db": velocity_db(pwl_acc, f),
           "energy_ratio": p_rad / input_power_per_accel(resp)}
    at = lambda y, x: float(np.interp(math.log(x), np.log(f), y))  # noqa: E731
    er = per["energy_ratio"]
    s = {"n_freqs": int(f.size), "fx_hz": fx_hz, "ref_hz": ref_hz,
         **load_pieces(f, z.real, fx_hz, loaded_hi_hz),
         "probe_hz": list(probe_hz),
         "re_z_at_probe": [at(z.real, x) for x in probe_hz],
         "im_z_eng_at_probe": [at(-z.imag, x) for x in probe_hz],
         "gamma_at_probe": [at(per["gamma"], x) for x in probe_hz],
         "re_z_at_ref": at(z.real, ref_hz),
         "on_axis_vel_rel_ref_db": [rel_db(f, per["on_axis_vel_db"], x, ref_hz) for x in probe_hz],
         "power_vel_rel_ref_db": [rel_db(f, per["power_vel_db"], x, ref_hz) for x in probe_hz],
         "on_axis_acc_rel_ref_db_DO_NOT_USE_AS_OUTPUT": [rel_db(f, on_acc, x, ref_hz) for x in probe_hz],
         "power_vel_residual_max_std_db": detrended_residual(f, per["power_vel_db"], *band),
         "on_axis_vel_residual_max_std_db": detrended_residual(f, per["on_axis_vel_db"], *band),
         "energy_ratio_min_max": [float(np.nanmin(er)), float(np.nanmax(er))]}
    if drivers:
        rows = []
        hp = butterworth_hp(f, fx_hz, hp_order) if hp_order else np.ones_like(f)
        for prm in drivers:
            out = drive(CompressionDriver.from_dict(prm), resp, volts_rms=2.83)
            spl = out["spl_onaxis_db"]
            pw = 10.0 * np.log10(out["acoustic_power_w"] / 1e-12)
            spl_hp = spl + 20.0 * np.log10(hp)
            rows.append({"driver": prm.get("name", "?"),
                         **{f"on_{int(x)}_rel_ref_db": rel_db(f, spl, x, ref_hz) for x in probe_hz},
                         **{f"hp_on_{int(x)}_rel_ref_db": rel_db(f, spl_hp, x, ref_hz) for x in probe_hz},
                         "power_828_rel_ref_db": rel_db(f, pw, 828.0, ref_hz),
                         "on_residual_max_db": detrended_residual(f, spl, *band)[0],
                         "power_residual_max_db": detrended_residual(f, pw, *band)[0]})
        s["driver_rows"] = rows
        s["driver_min_median_max"] = {k: [float(np.nanmin(v)), float(np.nanmedian(v)), float(np.nanmax(v))]
                                      for k in rows[0] if k != "driver"
                                      for v in [[r[k] for r in rows]]}
    return {"per_frequency": per, "summary": s}


# ----------------------------------------------------------------------------- CLI

def _parse_target(t: str) -> tuple[str, Path]:
    label, _, path = t.rpartition("=")
    p = Path(path)
    return (label or p.name), p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="+", help="[label=]path/to/designs/<hash>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fx", type=float, default=700.0, help="crossover / F_X, Hz (brief f0)")
    ap.add_argument("--ref", type=float, default=2000.0, help="reference frequency for rel. levels")
    ap.add_argument("--loaded-hi", type=float, default=5600.0, help="brief loaded_hi_hz")
    ap.add_argument("--driver", action="append", default=[], help="driver YAML (repeatable)")
    ap.add_argument("--no-bracket", action="store_true", help="no drivers unless --driver is given")
    ap.add_argument("--hp-order", type=int, default=2, help="Butterworth HP order at F_X (0 = none)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: {out} exists and is not empty")
    from hornlab_search.solve.cache import load_response
    import yaml
    drivers = [yaml.safe_load(Path(p).read_text(encoding="utf-8")) for p in a.driver]
    if not drivers and not a.no_bracket:
        drivers = bracket_drivers()
    out.mkdir(parents=True, exist_ok=True)
    summary, csv_rows, drv_rows = {}, [], []
    for t in a.targets:
        label, d = _parse_target(t)
        res = diagnose(load_response(d / "response.npz"), fx_hz=a.fx, ref_hz=a.ref,
                       loaded_hi_hz=a.loaded_hi, drivers=drivers, hp_order=a.hp_order)
        per = res["per_frequency"]
        for i in range(len(per["freq_hz"])):
            csv_rows.append({"design": label, **{k: float(v[i]) for k, v in per.items()}})
        for r in res["summary"].pop("driver_rows", []):
            drv_rows.append({"design": label, **r})
        summary[label] = {"design_dir": d.as_posix(), **res["summary"]}
    for name, rows in (("per_frequency.csv", csv_rows), ("driver_rows.csv", drv_rows)):
        if rows:
            with open(out / name, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    summary["_conventions"] = {
        "levels": "_acc = per unit throat acceleration (as stored); _vel = +20log10(w), per unit velocity",
        "z": "specific, /rho c; im_z_eng = -Im(z_bem), + = mass-like", "gamma": "plane-wave diagnostic only",
        "energy_ratio": "balloon power / (1/2 rho c Re z S |v|^2); ~1 = consistent data",
        "drivers": ("given YAMLs" if a.driver else "[inferred] bracket " + json.dumps(BRACKET)
                    + " + " + json.dumps(BRACKET_FIXED)) if drivers else "none",
        "hp": f"ideal Butterworth order {a.hp_order} at {a.fx:g} Hz" if a.hp_order else "none",
        "status": "REPORT-ONLY diagnostic; not a score term"}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=float, allow_nan=True),
                                      encoding="utf-8")
    lines = ["| design | Re z @ probes | power_vel rel ref (dB) | on-axis_vel rel ref (dB) | energy ratio | "
             "load_raw | driver on-axis rel ref, min/med/max @ 828 |", "|---|---|---|---|---|---|---|"]
    fmt = lambda v: "/".join(f"{x:+.1f}" if isinstance(x, float) and x == x else "nan" for x in v)  # noqa: E731
    for lab, s in summary.items():
        if lab.startswith("_"):
            continue
        dm = s.get("driver_min_median_max", {}).get("on_828_rel_ref_db")
        lines.append(f"| {lab} | {'/'.join(f'{x:.2f}' for x in s['re_z_at_probe'])} | "
                     f"{fmt(s['power_vel_rel_ref_db'])} | {fmt(s['on_axis_vel_rel_ref_db'])} | "
                     f"{s['energy_ratio_min_max'][0]:.2f}-{s['energy_ratio_min_max'][1]:.2f} | "
                     f"{s['load_raw']:.3f} | {fmt(dm) if dm else '-'} |")
    (out / "REPORT.md").write_text(
        "# XO loading diagnostics (report-only)\n\nProbe frequencies "
        + ", ".join(f"{x:g}" for x in summary[next(iter(summary))]["probe_hz"])
        + f" Hz; reference {a.ref:g} Hz; F_X {a.fx:g} Hz.\n\n" + "\n".join(lines) + "\n\n"
        + "Conventions: see `summary.json` `_conventions`.\n", encoding="utf-8")
    print((out / "REPORT.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
