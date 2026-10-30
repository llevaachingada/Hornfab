"""Lumped driver model over the BEM throat impedance (report-only, P12 2026-10-27; cone 2026-10-28).

Why: the solver drives an ideal throat (unit normal acceleration) and every pattern metric is normalised
to on-axis, so absolute level, sensitivity, excursion and efficiency are invisible. The horn solve does
not depend on the driver (only on the throat size it was meshed for), so any stored horn can be paired
with any driver of that exit size here, with no new solve. Research basis:
docs/research/SIM_VS_REAL_HORN_2026-10-27.md s2 / s5B (Akabak/Hornresp/Boundary Lab pattern: LEM driver
over a BEM radiation load; use the DRY moving mass Mmd, not an Mms that already contains air load).

Two driver kinds (``kind``; the default ``"compression"`` keeps every earlier driver and test number
byte-identical):

* ``"compression"`` - a compression driver: diaphragm area Sd behind a phase plug, optional front
  (compression) chamber, optional rear chamber from an explicit Cms.
* ``"cone"`` - a paper-cone driver in a sealed rear bowl: Sd is the cone face area projected on the
  axis, the front chamber (cone chamber + throat ring) is already in the BEM mesh, so
  ``front_chamber_cm3`` must be 0 (V1 = 0) and the rear load is the sealed bowl's NET air volume
  ``rear_box_l`` (litres; driver motor volume already subtracted by the measurement).

Circuit (engineering time convention exp(+j w t); rms quantities), mechanical side referred to the
diaphragm:

    Ze   = Re + j w Le                              voice coil, plain Le (le_mh)
    Ze   = Re + j w Le + (j w L2 R2)/(R2 + j w L2)  same, semi-inductance LR-2 alternative
                                                    (l2_mh + r2_ohm, both or neither)
    Zm   = Rms + j w M + 1/(j w Cms)                suspension and moving mass, M = Mmd
                                                    (or Mms - air_load_g when the split is known)
    ZtA  = rho c z / A                              acoustic load at the throat (BEM, area A)
    Zf   = ZtA || 1/(j w Caf),  Caf = V1/(rho c^2)  front (compression) chamber shunt, V1 >= 0
                                                    (V1 = 0 for kind cone: it is in the mesh)
    Zr   = 1/(j w Cab)                              rear chamber/bowl compliance, Cab = Vb/(rho c^2)
    Zr  += 1/(2 pi fs Qb Cab)                       box loss, only with rear_box_q  [inferred]
    Zr  += j w M_air,  M_air = rear_air_mass_g/Sd^2 diagnostic folded-column upper bound, default 0
    Sd_eff(f) = Sd / (1 + (f/f_b)^n)                break-up area law, only with f_breakup_hz [inferred]
    Zmot = Zm + Sd_eff^2 (Zf + Zr)
    I = E / (Ze + Bl^2/Zmot),  v = Bl I / Zmot,  Ud = Sd_eff v,  Ut = Ud * Zc / (ZtA + Zc)
                                                    (Zc = 1/(j w Caf), split = 1 when V1 = 0)

Vb is ``rear_box_l`` x 1e-3 when that key is present, else the legacy ``rear_chamber_cm3`` (only with
an explicit ``cms_mm_per_n``; a published fs already includes the driver's own rear chamber). No box air
mass is added by default: the lumped sealed-box load is compliance-only, and a folded-column mass
``rho Vb/Sd^2`` is not the physical box load (it would wrongly raise fs); ``rear_air_mass_g`` is the
explicitly opt-in diagnostic upper bound.

The phase-plug channels are treated as short and lossless (pressure and volume velocity continuous from
the chamber to the throat), so the effective compression ratio is Sd / A. The BEM stores z in its own
exp(-i w t) convention (mass-like loading has Im z < 0, NOTES_FOR_SENIOR z_throat note); this module uses
conj(z). On-axis pressure: |p| = |H| w |Ut| / A with H the stored on-axis pressure per unit acceleration,
extrapolated from the stored distance to ``ref_distance_m`` by 1/r. Break-up scales BOTH the acoustic
load and the radiated volume velocity by Sd_eff, so the circuit stays lossless either way.

Validity [inferred]: good where the driver behaves as a piston into a compliant chamber - roughly from fs
to the first internal phase-plug/chamber mode (a few kHz for 1.4-2" drivers). For a paper cone, a plain
Le stops describing the voice-coil impedance above ~1 kHz, so the LR-2 block is preferred there; its
FORM is standard (Leach/Wright), its VALUES come from the impedance measurement's fit. Cone break-up is
rigid-piston below ~1-1.5 kHz and ``f_breakup_hz`` is a labelled [inferred] placeholder until a
laser/accelerometer profile exists. Absolute accuracy is limited by the datasheet (Bl, Mmd, Re);
RELATIVE results (horn A vs horn B on one driver) are much tighter. Pure numpy.
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
                 "le_mh", "l2_mh", "r2_ohm", "rear_chamber_cm3", "front_chamber_cm3", "rear_box_l",
                 "rear_box_q", "rear_air_mass_g", "air_load_g", "f_breakup_hz", "breakup_exponent",
                 "exit_diameter_mm", "nominal_impedance_ohm", "xmax_mm", "power_aes_w",
                 "min_crossover_hz", "published_sensitivity_db")
_OPTIONAL_STR = ("source", "notes", "use", "kind", "published_sensitivity_condition")


def _pos(name: str, v, *, allow_zero: bool = False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"driver.{name} must be a number, got {v!r}")
    x = float(v)
    if not math.isfinite(x) or x < 0.0 or (x == 0.0 and not allow_zero):
        raise ValueError(f"driver.{name} must be a finite number {'>= 0' if allow_zero else '> 0'}, got {v!r}")
    return x


@dataclass(frozen=True)
class CompressionDriver:
    """Datasheet parameters of one driver, plus the derived SI values the circuit uses.

    Inputs in datasheet units. Required: ``name``, ``re_ohm``, ``sd_cm2``; one of ``mmd_g`` (preferred)
    or ``mms_g``; one of ``bl_tm`` or ``qes``; one of ``fs_hz`` or ``cms_mm_per_n``; one of ``qms``,
    ``rms_kg_s`` or (``qts`` and ``qes``). ``fs_hz`` is taken as the driver's published resonance with its
    own rear chamber, so ``rear_chamber_cm3`` is used only together with an explicit ``cms_mm_per_n``.

    ``kind`` is ``"compression"`` (default) or ``"cone"``. A cone file gives the sealed bowl's NET air
    volume as ``rear_box_l`` (litres) and must leave ``front_chamber_cm3`` at 0 (that front volume is in
    the BEM mesh). ``rear_box_q`` adds a series box-loss resistance; ``l2_mh`` + ``r2_ohm`` replace a
    plain ``le_mh`` with the LR-2 semi-inductance block; ``air_load_g`` splits a published ``mms_g``;
    ``f_breakup_hz`` + ``breakup_exponent`` apply the [inferred] effective-area law. ``rear_air_mass_g``
    is an explicitly opt-in diagnostic upper bound and is never on by default.
    """

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
    kind: str = "compression"
    rear_box_m3: float | None = None       # sealed rear bowl volume, m^3 (rear_box_l)
    rear_box_q: float | None = None        # sealed box loss Q (series acoustic resistance) [inferred]
    rear_air_mass_g: float = 0.0           # opt-in diagnostic folded-column mass upper bound
    l2_h: float = 0.0                      # LR-2 semi-inductance, henry
    r2_ohm: float = 0.0                    # LR-2 semi-inductance, ohm
    air_load_g: float | None = None        # front free-air load split out of mms_g
    f_breakup_hz: float | None = None      # [inferred] effective-area break-up corner
    breakup_exponent: float = 2.0          # [inferred] effective-area law exponent
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def sd_m2(self) -> float:
        return self.sd_cm2 * 1e-4

    @property
    def fs_hz(self) -> float:
        return 1.0 / (2.0 * math.pi * math.sqrt(self.m_kg * self.cms_m_per_n))

    @property
    def inductance_model(self) -> str:
        """``"plain"`` (single ``le_mh``) or ``"lr2"`` (LR-2 block, ``l2_mh`` + ``r2_ohm``)."""
        return "lr2" if self.l2_h else "plain"

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
        kind = str(d.get("kind") or "compression")
        if kind not in ("compression", "cone"):
            raise ValueError(f"driver.kind must be 'compression' or 'cone', got {kind!r}")
        num = {k: _pos(k, d[k], allow_zero=k in ("le_mh", "front_chamber_cm3", "rear_air_mass_g"))
               for k in _OPTIONAL_NUM if d.get(k) is not None}
        re_ohm = _pos("re_ohm", d["re_ohm"])
        sd_cm2 = _pos("sd_cm2", d["sd_cm2"])

        if "mmd_g" in num:
            if "air_load_g" in num:
                raise ValueError("driver.air_load_g only splits a published mms_g; mmd_g is already dry")
            m, air = num["mmd_g"] * 1e-3, False
        elif "mms_g" in num:
            if "air_load_g" in num:
                if num["air_load_g"] >= num["mms_g"]:
                    raise ValueError("driver.air_load_g must be smaller than mms_g "
                                     "(the front air load cannot exceed the published moving mass)")
                m, air = (num["mms_g"] - num["air_load_g"]) * 1e-3, False
            else:
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
        front = num.get("front_chamber_cm3", 0.0) * 1e-6
        if kind == "cone" and front > 0.0:
            raise ValueError("driver.kind 'cone': front_chamber_cm3 must be 0 - the front chamber "
                             "(cone chamber + throat ring) is already in the BEM mesh, so the circuit "
                             "must not add a second front compliance (V1 = 0)")
        rear_box = num["rear_box_l"] * 1e-3 if "rear_box_l" in num else None
        if "rear_box_q" in num and rear_box is None and rear is None:
            raise ValueError("driver.rear_box_q needs a rear volume (rear_box_l, or "
                             "rear_chamber_cm3 together with cms_mm_per_n)")
        if "rear_air_mass_g" in num and num["rear_air_mass_g"] > 0.0 and rear_box is None and rear is None:
            raise ValueError("driver.rear_air_mass_g needs a rear volume (rear_box_l) - "
                             "it is a diagnostic mass in series with the sealed-box compliance")

        has_l2, has_r2 = "l2_mh" in num, "r2_ohm" in num
        if has_l2 != has_r2:
            missing_lr2 = "r2_ohm" if has_l2 else "l2_mh"
            raise ValueError(f"driver: the LR-2 semi-inductance model needs l2_mh and r2_ohm together; "
                             f"missing {missing_lr2}")

        return cls(name=str(d["name"]), re_ohm=re_ohm, sd_cm2=sd_cm2, m_kg=m, cms_m_per_n=cms, rms_kg_s=rms,
                   bl_tm=bl, le_h=num.get("le_mh", 0.0) * 1e-3, rear_chamber_m3=rear,
                   front_chamber_m3=front,
                   exit_diameter_mm=num.get("exit_diameter_mm"),
                   nominal_impedance_ohm=num.get("nominal_impedance_ohm"),
                   xmax_mm=num.get("xmax_mm"), power_aes_w=num.get("power_aes_w"),
                   min_crossover_hz=num.get("min_crossover_hz"),
                   published_sensitivity_db=num.get("published_sensitivity_db"),
                   published_sensitivity_condition=str(d.get("published_sensitivity_condition") or ""),
                   mass_may_include_air_load=air, use=str(d.get("use") or ""),
                   source=str(d.get("source") or ""), notes=str(d.get("notes") or ""),
                   kind=kind, rear_box_m3=rear_box, rear_box_q=num.get("rear_box_q"),
                   rear_air_mass_g=num.get("rear_air_mass_g", 0.0),
                   l2_h=num.get("l2_mh", 0.0) * 1e-3, r2_ohm=num.get("r2_ohm", 0.0),
                   air_load_g=num.get("air_load_g"),
                   f_breakup_hz=num.get("f_breakup_hz"),
                   breakup_exponent=num.get("breakup_exponent", 2.0), raw=dict(d))

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
    ``throat_velocity_mps``, ``sd_eff_m2`` (the effective radiating area used; equal to Sd unless a
    break-up corner is set); scalars ``volts_rms``, ``throat_area_m2`` (the driven source area),
    ``compression_ratio`` (Sd / A), ``kind``, ``breakup_applied``, ``rear_box_m3`` and
    ``inductance_model`` ('plain' / 'lr2'). The throat SHAPE versus the driver exit is checked from the
    mesh by tools/loudness_report.py (an aspect-stretched OS throat has the right area class but the
    wrong shape). Raises ``ValueError`` when the response has no throat impedance or no usable throat
    area."""
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
    if d.inductance_model == "lr2":                      # Leach/Wright LR-2 semi-inductance block
        zl2 = jw * d.l2_h
        ze = ze + zl2 * d.r2_ohm / (d.r2_ohm + zl2)
    zm = d.rms_kg_s + jw * d.m_kg + 1.0 / (jw * d.cms_m_per_n)
    zta = _load_impedance(resp, area)
    if d.front_chamber_m3 > 0.0:
        zc = 1.0 / (jw * d.front_chamber_m3 / rho_c2)
        zf = zta * zc / (zta + zc)
        split = zc / (zta + zc)
    else:
        zf = zta
        split = np.ones_like(zta)
    vb = d.rear_box_m3 if d.rear_box_m3 is not None else d.rear_chamber_m3
    if vb:
        cab = vb / rho_c2
        zr = 1.0 / (jw * vb / rho_c2)                    # compliance-only sealed-box load (no air mass)
        if d.rear_box_q:                                 # [inferred] leak/stuffing loss, series resistance
            zr = zr + 1.0 / (2.0 * math.pi * d.fs_hz * d.rear_box_q * cab)
        if d.rear_air_mass_g:                            # opt-in diagnostic upper bound, default off
            zr = zr + jw * (d.rear_air_mass_g * 1e-3 / sd ** 2)
    else:
        zr = 0.0
    if d.f_breakup_hz:                                   # [inferred] effective area shrinks above f_b
        sd_eff = sd / (1.0 + (f / d.f_breakup_hz) ** d.breakup_exponent)
        load = sd_eff ** 2 * (zf + zr)
    else:
        sd_eff = np.full(f.shape, sd)
        load = sd ** 2 * (zf + zr)
    zmot = zm + load
    z_in = ze + d.bl_tm ** 2 / zmot
    i = float(volts_rms) / z_in
    v = d.bl_tm * i / zmot
    ud = sd_eff * v
    ut = ud * split
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
            "kind": d.kind,
            "sd_eff_m2": np.asarray(sd_eff, dtype=float),
            "breakup_applied": bool(d.f_breakup_hz is not None),
            "rear_box_m3": d.rear_box_m3,
            "inductance_model": d.inductance_model,
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
    return [str(k) for k in (*_REQUIRED, *_OPTIONAL_NUM, *_OPTIONAL_STR)]
