"""Lumped compression-driver model over the BEM throat impedance (report-only, P12 2026-10-27).

Why: the solver drives an ideal throat (unit normal acceleration) and every pattern metric is normalised
to on-axis, so absolute level, sensitivity, excursion and efficiency are invisible. The horn solve does
not depend on the driver (only on the throat size it was meshed for), so any stored horn can be paired
with any driver of that exit size here, with no new solve. Research basis:
docs/research/SIM_VS_REAL_HORN_2026-10-27.md s2 / s5B (Akabak/Hornresp/Boundary Lab pattern: LEM driver
over a BEM radiation load; use the DRY moving mass Mmd, not an Mms that already contains air load).

Circuit (engineering time convention exp(+j w t); rms quantities), mechanical side referred to the
diaphragm:

    Ze   = Re + j w Le                              voice coil
    Zm   = Rms + j w Mmd + 1/(j w Cms)              suspension and moving mass
    ZtA  = rho c z / A                              acoustic load at the throat (BEM, area A)
    Zf   = ZtA || 1/(j w Caf),  Caf = V1/(rho c^2)  front (compression) chamber shunt, V1 >= 0
    Zr   = 1/(j w Cab),  Cab = Vb/(rho c^2)         rear chamber, only when Cms is given explicitly
    Zmot = Zm + Sd^2 (Zf + Zr)
    I = E / (Ze + Bl^2/Zmot),  v = Bl I / Zmot,  Ud = Sd v,  Ut = Ud * Zc / (ZtA + Zc)  (Zc = 1/(j w Caf))

The phase-plug channels are treated as short and lossless (pressure and volume velocity continuous from
the chamber to the throat), so the effective compression ratio is Sd / A. The BEM stores z in its own
exp(-i w t) convention (mass-like loading has Im z < 0, NOTES_FOR_SENIOR z_throat note); this module uses
conj(z). On-axis pressure: |p| = |H| w |Ut| / A with H the stored on-axis pressure per unit acceleration,
extrapolated from the stored distance to ``ref_distance_m`` by 1/r.

Validity [inferred]: good where the driver behaves as a piston into a compliant chamber - roughly from fs
to the first internal phase-plug/chamber mode (a few kHz for 1.4-2" drivers). Above that the published
response of the driver on a plane-wave tube is the better guide. Absolute accuracy is limited by the
datasheet (Bl, Mmd, Re); RELATIVE results (horn A vs horn B on one driver) are much tighter.
Pure numpy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..constants import C_AIR, REF_P, RHO_AIR
from ..metrics.loudness import onaxis_pressure_per_accel, throat_area_m2

__all__ = ["CompressionDriver", "drive", "band_mean_db", "max_spl_db"]

_REQUIRED = ("name", "re_ohm", "sd_cm2")
_OPTIONAL_NUM = ("bl_tm", "qes", "qms", "qts", "rms_kg_s", "mmd_g", "mms_g", "fs_hz", "cms_mm_per_n",
                 "le_mh", "rear_chamber_cm3", "front_chamber_cm3", "exit_diameter_mm",
                 "nominal_impedance_ohm", "xmax_mm", "power_aes_w", "min_crossover_hz",
                 "published_sensitivity_db")
_OPTIONAL_STR = ("source", "notes", "use", "published_sensitivity_condition")


def _pos(name: str, v, *, allow_zero: bool = False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"driver.{name} must be a number, got {v!r}")
    x = float(v)
    if not math.isfinite(x) or x < 0.0 or (x == 0.0 and not allow_zero):
        raise ValueError(f"driver.{name} must be a finite number {'>= 0' if allow_zero else '> 0'}, got {v!r}")
    return x


@dataclass(frozen=True)
class CompressionDriver:
    """Datasheet parameters of one compression driver, plus the derived SI values the circuit uses.

    Inputs in datasheet units. Required: ``name``, ``re_ohm``, ``sd_cm2``; one of ``mmd_g`` (preferred)
    or ``mms_g``; one of ``bl_tm`` or ``qes``; one of ``fs_hz`` or ``cms_mm_per_n``; one of ``qms``,
    ``rms_kg_s`` or (``qts`` and ``qes``). ``fs_hz`` is taken as the driver's published resonance with its
    own rear chamber, so ``rear_chamber_cm3`` is used only together with an explicit ``cms_mm_per_n``."""

    name: str
    re_ohm: float
    sd_cm2: float
    m_kg: float                      # moving mass used (Mmd, or Mms when that is all there is)
    cms_m_per_n: float
    rms_kg_s: float
    bl_tm: float
    le_h: float = 0.0
    rear_chamber_m3: float | None = None
    front_chamber_m3: float = 0.0
    exit_diameter_mm: float | None = None
    nominal_impedance_ohm: float | None = None
    xmax_mm: float | None = None
    power_aes_w: float | None = None
    min_crossover_hz: float | None = None
    published_sensitivity_db: float | None = None
    published_sensitivity_condition: str = ""
    mass_may_include_air_load: bool = False
    use: str = ""
    source: str = ""
    notes: str = ""
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def sd_m2(self) -> float:
        return self.sd_cm2 * 1e-4

    @property
    def fs_hz(self) -> float:
        return 1.0 / (2.0 * math.pi * math.sqrt(self.m_kg * self.cms_m_per_n))

    @classmethod
    def from_dict(cls, d: dict) -> "CompressionDriver":
        if not isinstance(d, dict):
            raise ValueError("driver must be a mapping")
        known = set(_REQUIRED) | set(_OPTIONAL_NUM) | set(_OPTIONAL_STR)
        unknown = sorted(set(d) - known)
        if unknown:
            raise ValueError(f"driver: unknown key(s) {unknown} (known: {sorted(known)})")
        missing = [k for k in _REQUIRED if d.get(k) is None]
        if missing:
            raise ValueError(f"driver: missing required key(s) {missing}")
        num = {k: _pos(k, d[k], allow_zero=k in ("le_mh", "front_chamber_cm3"))
               for k in _OPTIONAL_NUM if d.get(k) is not None}
        re_ohm = _pos("re_ohm", d["re_ohm"])
        sd_cm2 = _pos("sd_cm2", d["sd_cm2"])

        if "mmd_g" in num:
            m, air = num["mmd_g"] * 1e-3, False
        elif "mms_g" in num:
            m, air = num["mms_g"] * 1e-3, True
        else:
            raise ValueError("driver: give mmd_g (moving mass without air load; preferred) or mms_g")

        if "cms_mm_per_n" in num:
            cms = num["cms_mm_per_n"] * 1e-3
            fs = 1.0 / (2.0 * math.pi * math.sqrt(m * cms))
        elif "fs_hz" in num:
            fs = num["fs_hz"]
            cms = 1.0 / ((2.0 * math.pi * fs) ** 2 * m)
        else:
            raise ValueError("driver: give fs_hz (published resonance) or cms_mm_per_n")

        qes = num.get("qes")
        if "rms_kg_s" in num:
            rms = num["rms_kg_s"]
        elif "qms" in num:
            rms = 2.0 * math.pi * fs * m / num["qms"]
        elif "qts" in num and qes is not None:
            if not num["qts"] < qes:
                raise ValueError("driver: qts must be smaller than qes to derive qms")
            qms = 1.0 / (1.0 / num["qts"] - 1.0 / qes)
            rms = 2.0 * math.pi * fs * m / qms
        else:
            raise ValueError("driver: give qms, rms_kg_s, or both qts and qes")

        if "bl_tm" in num:
            bl = num["bl_tm"]
        elif qes is not None:
            bl = math.sqrt(2.0 * math.pi * fs * m * re_ohm / qes)
        else:
            raise ValueError("driver: give bl_tm or qes")

        rear = num["rear_chamber_cm3"] * 1e-6 if ("rear_chamber_cm3" in num and "cms_mm_per_n" in num) else None
        return cls(name=str(d["name"]), re_ohm=re_ohm, sd_cm2=sd_cm2, m_kg=m, cms_m_per_n=cms, rms_kg_s=rms,
                   bl_tm=bl, le_h=num.get("le_mh", 0.0) * 1e-3, rear_chamber_m3=rear,
                   front_chamber_m3=num.get("front_chamber_cm3", 0.0) * 1e-6,
                   exit_diameter_mm=num.get("exit_diameter_mm"),
                   nominal_impedance_ohm=num.get("nominal_impedance_ohm"),
                   xmax_mm=num.get("xmax_mm"), power_aes_w=num.get("power_aes_w"),
                   min_crossover_hz=num.get("min_crossover_hz"),
                   published_sensitivity_db=num.get("published_sensitivity_db"),
                   published_sensitivity_condition=str(d.get("published_sensitivity_condition") or ""),
                   mass_may_include_air_load=air, use=str(d.get("use") or ""),
                   source=str(d.get("source") or ""), notes=str(d.get("notes") or ""), raw=dict(d))

    @classmethod
    def from_yaml(cls, path) -> "CompressionDriver":
        import yaml
        with open(Path(path), encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))

    def volts_for_watts(self, watts: float = 1.0) -> float:
        """Voltage that delivers ``watts`` into the nominal impedance (Re when no nominal is given)."""
        z = self.nominal_impedance_ohm or self.re_ohm
        return math.sqrt(float(watts) * z)


def _load_impedance(resp, area: float) -> np.ndarray:
    """Acoustic impedance rho c z / A at the throat, engineering convention (conj of the BEM's)."""
    z = np.conj(np.asarray(resp.z_throat, dtype=complex))
    return RHO_AIR * C_AIR * z / area


def drive(driver: CompressionDriver, resp, *, volts_rms: float = 2.83, ref_distance_m: float = 1.0) -> dict:
    """Drive ``driver`` at ``volts_rms`` into the horn of stored Response ``resp``.

    Returns per-frequency arrays: ``freqs_hz``, ``spl_onaxis_db`` (at ``ref_distance_m``), ``excursion_mm_peak``,
    ``z_in_ohm`` (complex electrical input impedance), ``acoustic_power_w``, ``efficiency_pct``,
    ``throat_velocity_mps``; scalars ``volts_rms``, ``throat_area_m2`` (the driven source area) and
    ``compression_ratio`` (Sd / A). The throat SHAPE versus the driver exit is checked from the mesh by
    tools/loudness_report.py (an aspect-stretched OS throat has the right area class but the wrong shape).
    Raises ``ValueError`` when the response has no throat impedance or no usable throat area."""
    if resp.z_throat is None:
        raise ValueError("drive: the response has no throat impedance (z_throat)")
    area = throat_area_m2(resp)
    if not np.isfinite(area):
        raise ValueError("drive: the response carries no throat area (meta.physical_tag_areas_m2)")
    f = np.asarray(resp.freqs_hz, dtype=float)
    w = 2.0 * np.pi * f
    jw = 1j * w
    d = driver
    sd = d.sd_m2
    rho_c2 = RHO_AIR * C_AIR ** 2

    ze = d.re_ohm + jw * d.le_h
    zm = d.rms_kg_s + jw * d.m_kg + 1.0 / (jw * d.cms_m_per_n)
    zta = _load_impedance(resp, area)
    if d.front_chamber_m3 > 0.0:
        zc = 1.0 / (jw * d.front_chamber_m3 / rho_c2)
        zf = zta * zc / (zta + zc)
        split = zc / (zta + zc)
    else:
        zf = zta
        split = np.ones_like(zta)
    zr = 1.0 / (jw * d.rear_chamber_m3 / rho_c2) if d.rear_chamber_m3 else 0.0
    zmot = zm + sd ** 2 * (zf + zr)
    z_in = ze + d.bl_tm ** 2 / zmot
    i = float(volts_rms) / z_in
    v = d.bl_tm * i / zmot
    ut = sd * v * split
    vt = ut / area

    r = float((resp.meta or {}).get("distance_m", float("nan")))
    p_axis = onaxis_pressure_per_accel(resp) * w * np.abs(vt) * (r / float(ref_distance_m))
    p_in = np.real(float(volts_rms) * np.conj(i))
    p_ac = np.real(zta) * np.abs(ut) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        out = {
            "freqs_hz": f,
            "spl_onaxis_db": 20.0 * np.log10(p_axis / REF_P),
            "excursion_mm_peak": math.sqrt(2.0) * np.abs(v) / w * 1e3,
            "z_in_ohm": z_in,
            "acoustic_power_w": p_ac,
            "efficiency_pct": 100.0 * p_ac / p_in,
            "throat_velocity_mps": np.abs(vt),
            "volts_rms": float(volts_rms),
            "throat_area_m2": area,
            "compression_ratio": sd / area,
        }
    return out


def band_mean_db(freqs_hz, level_db, lo_hz: float, hi_hz: float) -> float:
    """Power-average of a dB curve over [lo, hi] (the solved points inside it). NaN if none."""
    f = np.asarray(freqs_hz, dtype=float)
    x = np.asarray(level_db, dtype=float)
    sel = (f >= lo_hz) & (f <= hi_hz) & np.isfinite(x)
    if not sel.any():
        return float("nan")
    return float(10.0 * np.log10(np.mean(10.0 ** (x[sel] / 10.0))))


def max_spl_db(driver: CompressionDriver, resp, *, ref_distance_m: float = 1.0) -> dict:
    """Maximum on-axis SPL per frequency, limited by the rated power (``power_aes_w``) and, when given, the
    peak excursion limit (``xmax_mm``). Linear model: no compression, no distortion. Returns
    ``max_spl_db`` and ``limit`` ('power' / 'excursion' per frequency); NaN where no limit is known."""
    one_w = drive(driver, resp, volts_rms=driver.volts_for_watts(1.0), ref_distance_m=ref_distance_m)
    f = one_w["freqs_hz"]
    head_p = 10.0 * math.log10(driver.power_aes_w) if driver.power_aes_w else np.nan
    head = np.full(f.shape, head_p, dtype=float)
    limit = np.array(["power" if driver.power_aes_w else ""] * f.size, dtype=object)
    if driver.xmax_mm:
        head_x = 20.0 * np.log10(driver.xmax_mm / one_w["excursion_mm_peak"])
        use_x = ~np.isfinite(head) | (head_x < head)
        head = np.where(use_x, head_x, head)
        limit = np.where(use_x, "excursion", limit)
    return {"freqs_hz": f, "max_spl_db": one_w["spl_onaxis_db"] + head, "limit": limit,
            "spl_1w_db": one_w["spl_onaxis_db"]}


def driver_fields() -> list[str]:
    """Every YAML key a driver file may carry (for the template and error messages)."""
    return list(_REQUIRED) + list(_OPTIONAL_NUM) + list(_OPTIONAL_STR)
