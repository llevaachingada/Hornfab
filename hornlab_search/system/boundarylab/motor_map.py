"""Committed driver T/S -> Boundary Lab component parameters (unit-checked, no guessing).

Why this module exists
----------------------
The installed vented-enclosure provider hard-codes Boundary Lab's demo motor in
``geometry_providers/vented_enclosure/enclosure/backend.py`` (``parameters.DRIVER_DEFAULTS``).
Source overrides cannot change it. Boundary Lab's sanctioned route is the configuration patch:
``src/blab/generators/configuration.py`` accepts ``component_parameters`` as a
``PATCH_SECTIONS`` member and ``apply_configuration_patch`` upserts it per component id.

This module maps the committed, vendor-verified FaitalPRO 12PR300 data
(``examples/systems/driver_ts/faitalpro_12pr300.yaml``) onto BL's exact parameter names and
units. Every value is read from that YAML; every factor is stated. A missing BL-required field
is refused with :data:`MOTOR_FIELD_UNAVAILABLE` (never imputed).

Geometry is a separate, stricter story: ``examples/systems/driver_geometry/faitalpro_12pr300.yaml``
records only the publisher-printed ``cutout_mm``/``frame_od_mm``/``depth_mm``. BL's moving-surface
fields (cone depth, surround width, dust cap) are *not* printed and stay refused with
:data:`GEOMETRY_FIELD_UNAVAILABLE`; only ``driver_diameter_m`` is derived (from ``Sd``).

No ``blab`` import happens here: this is host-side mapping and staging-spec construction. The
BL-side execution lives in :mod:`hornlab_search.system.boundarylab.runner_motor_stage`.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from hornlab_search.meh.drivers import C_AIR, RHO_AIR
from hornlab_search.system import bass_reference, provenance
from hornlab_search.system.boundarylab import run as bl_run
from hornlab_search.system.boundarylab.generate import (
    _MAX_LOG_LINES,
    _execute,
    _parse_final_json,
)
from hornlab_search.system.boundarylab.probe import BLCapabilityError, BLRoot
from hornlab_search.system.contracts import BoxPoint, canonical_json

__all__ = [
    "BL_MOTOR_PARAMETER_KEYS",
    "EXPERIMENT_ID",
    "GEOMETRY_FIELD_UNAVAILABLE",
    "GEOMETRY_REQUIRED_FIELDS",
    "MOTOR_FIELD_UNAVAILABLE",
    "MOTOR_GEOMETRY_INCOMPLETE",
    "GeometryOverrides",
    "MotorMapping",
    "MotorStagedProject",
    "SeedReference",
    "build_motor_stage_spec",
    "geometry_overrides",
    "load_seed_reference_box",
    "map_motor",
    "panel_placement",
    "runner_path",
    "stage_motor_project",
    "vented_source",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
TS_PATH = REPO_ROOT / "examples" / "systems" / "driver_ts" / "faitalpro_12pr300.yaml"
GEOMETRY_PATH = REPO_ROOT / "examples" / "systems" / "driver_geometry" / "faitalpro_12pr300.yaml"
SEED_PATH = REPO_ROOT / "system_runs" / "woofer_seed_stage5_blfit" / "woofer_seed.json"
SEED_CANDIDATE_ID = "42d171062dcda386"
EXPERIMENT_ID = "bl_motor12pr"

#: BL's exact ``DRIVER_DEFAULTS`` keys (backend.py line 56 / parameters.py lines 34-43).
BL_MOTOR_PARAMETER_KEYS: tuple[str, ...] = (
    "re_ohm",
    "le_h",
    "bl_n_per_a",
    "mmd_kg",
    "cms_m_per_n",
    "rms_n_s_per_m",
    "motion_profile",
    "motion_axis",
)

#: BL transducer source fields needed for a real moving-surface geometry.
GEOMETRY_REQUIRED_FIELDS: tuple[str, ...] = (
    "driver_diameter_m",
    "cone_depth_m",
    "surround_width_m",
    "cap_diameter_m",
    "driver_y_m",
)

#: Refusal tokens (explicit, never imputed).
MOTOR_FIELD_UNAVAILABLE = "MOTOR_FIELD_UNAVAILABLE"
GEOMETRY_FIELD_UNAVAILABLE = "GEOMETRY_FIELD_UNAVAILABLE"
MOTOR_GEOMETRY_INCOMPLETE = "MOTOR_GEOMETRY_INCOMPLETE"

#: BL's moving-surface placement clearance (parameters.py line 100) and LF-tier port convention.
BL_VALIDATE_CLEARANCE_M = 0.003

#: Source files this staging depends on (hashed into every case manifest).
_MOTOR_STAGE_DEPENDENCIES: tuple[str, ...] = (
    "src/blab/generators/__init__.py",
    "src/blab/generators/application.py",
    "src/blab/generators/base.py",
    "src/blab/generators/catalog.py",
    "src/blab/generators/configuration.py",
    "src/blab/headless.py",
    "src/blab/physical_compiler.py",
    "src/blab/physical_model.py",
    "src/blab/project/io.py",
    "src/blab/project/model.py",
    "src/blab/system_solve.py",
    "geometry_providers/vented_enclosure/provider.json",
    "geometry_providers/vented_enclosure/enclosure/backend.py",
    "geometry_providers/vented_enclosure/enclosure/parameters.py",
)


# --------------------------------------------------------------------------- helpers

def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(data: Mapping[str, Any], key: str) -> float | None:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _load_yaml(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _percent_error(model: float, published: float) -> float:
    return abs(model - published) / published * 100.0


# --------------------------------------------------------------------------- motor mapping

@dataclass(frozen=True)
class MotorMapping:
    """Committed T/S -> BL component parameters, with every factor and refusal on the record."""

    driver_id: str
    ts_path: str
    ts_sha256: str
    parameters: Mapping[str, Any]
    field_map: Mapping[str, Mapping[str, Any]]
    refusals: Mapping[str, str]
    cross_checks: Mapping[str, Any]
    dry_mass_kg: float | None

    @property
    def ok(self) -> bool:
        return not self.refusals

    def patch(self, document_id: str) -> dict[str, Any]:
        """The BL configuration patch section (component id + parameter mapping)."""
        if not document_id or "/" in document_id:
            raise ValueError(f"document_id must be a simple non-empty id, got {document_id!r}")
        if not self.ok:
            raise ValueError(
                "cannot build a component-parameters patch while motor fields are unavailable: "
                + json.dumps(dict(self.refusals), sort_keys=True))
        return {"component_parameters": {f"{document_id}/driver": dict(self.parameters)}}

    def to_record(self) -> dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "ts_path": self.ts_path,
            "ts_sha256": self.ts_sha256,
            "field_map": {key: dict(value) for key, value in self.field_map.items()},
            "parameters": dict(self.parameters),
            "refusals": dict(self.refusals),
            "cross_checks": dict(self.cross_checks),
            "dry_mass_kg": self.dry_mass_kg,
            "ok": self.ok,
            "bl_motor_parameter_keys": list(BL_MOTOR_PARAMETER_KEYS),
        }


def map_motor(path: str | Path = TS_PATH) -> MotorMapping:
    """Map one committed driver T/S YAML onto BL's ``DRIVER_DEFAULTS`` names and units.

    ``mmd_kg`` is the manufacturer's **dry** moving mass (``mmd_g`` / 1000). No air-load
    conversion is applied: BL's ``mmd_kg`` is also the dry mass (backend.py line 56 copies
    ``DRIVER_DEFAULTS`` where ``mmd_kg`` is 0.035 kg, not Mms). ``motion_profile`` and
    ``motion_axis`` are taken from BL's defaults only.
    """
    ts_path = Path(path)
    data = _load_yaml(ts_path)
    refusals: dict[str, str] = {}
    parameters: dict[str, Any] = {}
    field_map: dict[str, Mapping[str, Any]] = {}

    specs = (
        ("re_ohm", "re_ohm", 1.0, "ohm"),
        ("le_h", "le_mh", 1e-3, "H (datasheet mH -> H)"),
        ("bl_n_per_a", "bl_tm", 1.0, "N/A (T*m == N/A)"),
        ("mmd_kg", "mmd_g", 1e-3, "kg, DRY moving mass (datasheet g -> kg; no air load)"),
        ("cms_m_per_n", "cms_mm_per_n", 1e-3, "m/N (datasheet mm/N -> m/N)"),
        ("rms_n_s_per_m", "rms_kg_s", 1.0, "N*s/m (kg/s == N*s/m)"),
    )
    for bl_name, yaml_name, factor, unit in specs:
        value = _number(data, yaml_name)
        if value is None:
            refusals[bl_name] = MOTOR_FIELD_UNAVAILABLE
            continue
        parameters[bl_name] = round(value * factor, 15)
        field_map[bl_name] = {
            "yaml_field": yaml_name,
            "factor": factor,
            "unit": unit,
        }

    # Motion fields: BL defaults only (parameters.py lines 41-42), never invented here.
    parameters["motion_profile"] = "rigid_translation"
    parameters["motion_axis"] = [0, 0, 1]
    field_map["motion_profile"] = {
        "yaml_field": None, "factor": None, "unit": "",
        "source": "BL DRIVER_DEFAULTS (parameters.py line 41)",
    }
    field_map["motion_axis"] = {
        "yaml_field": None, "factor": None, "unit": "",
        "source": "BL DRIVER_DEFAULTS (parameters.py line 42)",
    }

    cross_checks = _motor_cross_checks(data, parameters)
    dry_mass = parameters.get("mmd_kg")
    return MotorMapping(
        driver_id=str(data.get("name") or ts_path.stem),
        ts_path=str(ts_path),
        ts_sha256=_sha256_file(ts_path),
        parameters=parameters,
        field_map=field_map,
        refusals=refusals,
        cross_checks=cross_checks,
        dry_mass_kg=None if dry_mass is None else float(dry_mass),
    )


def _motor_cross_checks(data: Mapping[str, Any],
                        parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Repo-consistency checks: the existing model-Fs pattern plus Vas from Cms/Sd.

    ``Le`` and ``Bl`` have no algebraic cross-check from the machine-readable fields (the
    vendor's Qes is prose-only in this YAML), so they are reported as unchecked rather than
    "verified" by a fabricated relation.
    """
    checks: dict[str, Any] = {
        "fs_model": None,
        "fs_published_hz": _number(data, "fs_hz"),
        "fs_error_percent": None,
        "fs_within_8_percent": None,
        "mms_model_kg": None,
        "mms_published_g": _number(data, "mms_g"),
        "mms_error_percent": None,
        "vas_model_l": None,
        "vas_published_l": _number(data, "vas_l"),
        "vas_error_percent": None,
        "le_bl": {
            "checked": False,
            "reason": ("no machine-readable Qes/other independent relation in this YAML; "
                       "Le and Bl are committed vendor values passed through unchanged"),
        },
    }
    sd_cm2 = _number(data, "sd_cm2")
    mmd_kg = parameters.get("mmd_kg")
    cms = parameters.get("cms_m_per_n")
    fs = checks["fs_published_hz"]
    if sd_cm2 is not None and sd_cm2 > 0.0 and mmd_kg is not None and cms is not None:
        sd_m2 = sd_cm2 * 1e-4
        a_m = math.sqrt(sd_m2 / math.pi)
        air_load_kg = 2.0 * (8.0 / 3.0) * RHO_AIR * a_m ** 3
        mms_kg = float(mmd_kg) + air_load_kg
        checks["mms_model_kg"] = mms_kg
        checks["air_load_kg"] = air_load_kg
        if checks["mms_published_g"] is not None:
            checks["mms_error_percent"] = _percent_error(
                mms_kg * 1e3, float(checks["mms_published_g"]))
        if fs is not None and fs > 0.0:
            fs_model = 1.0 / (2.0 * math.pi * math.sqrt(mms_kg * float(cms)))
            checks["fs_model"] = fs_model
            checks["fs_error_percent"] = _percent_error(fs_model, float(fs))
            checks["fs_within_8_percent"] = checks["fs_error_percent"] <= 8.0
        checks["vas_model_l"] = (
            RHO_AIR * C_AIR ** 2 * sd_m2 ** 2 * float(cms) * 1e3)
        if checks["vas_published_l"] is not None:
            checks["vas_error_percent"] = _percent_error(
                checks["vas_model_l"], float(checks["vas_published_l"]))
    return checks


# --------------------------------------------------------------------------- geometry

@dataclass(frozen=True)
class GeometryOverrides:
    """BL transducer geometry overrides that are actually committed/derived (never guessed)."""

    driver_id: str
    geometry_path: str
    geometry_sha256: str
    values: Mapping[str, float]
    refusals: Mapping[str, str]
    present_fields: tuple[str, ...]
    derived: Mapping[str, str]

    @property
    def complete(self) -> bool:
        return not self.refusals

    def to_record(self) -> dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "geometry_path": self.geometry_path,
            "geometry_sha256": self.geometry_sha256,
            "values": dict(self.values),
            "refusals": dict(self.refusals),
            "present_fields": list(self.present_fields),
            "derived": dict(self.derived),
            "complete": self.complete,
            "required_fields": list(GEOMETRY_REQUIRED_FIELDS),
        }


def geometry_overrides(
    ts_path: str | Path = TS_PATH,
    geometry_path: str | Path = GEOMETRY_PATH,
) -> GeometryOverrides:
    """Real-driver BL geometry override set, with explicit tokens for missing fields.

    ``driver_diameter_m`` is derived from the committed ``Sd`` (``2*sqrt(Sd/pi)``, the same
    derivation the seed screen records as ``effective_piston_radius_m``). Cone depth, surround
    width and dust cap are *not* printed by the vendor and are therefore refused. ``driver_y_m``
    is a placement value, not printed geometry, and is also refused here.
    """
    geometry_path = Path(geometry_path)
    ts_path = Path(ts_path)
    geo_data = _load_yaml(geometry_path)
    ts_data = _load_yaml(ts_path)
    present = tuple(
        key for key in ("cutout_mm", "frame_od_mm", "depth_mm", "cone_depth_mm",
                        "surround_width_mm", "dust_cap_diameter_mm",
                        "mounting_depth_behind_baffle_mm")
        if _number(geo_data, key) is not None
    )
    values: dict[str, float] = {}
    refusals: dict[str, str] = {}
    derived: dict[str, str] = {}

    sd_cm2 = _number(ts_data, "sd_cm2")
    if sd_cm2 is not None and sd_cm2 > 0.0:
        values["driver_diameter_m"] = 2.0 * math.sqrt(sd_cm2 * 1e-4 / math.pi)
        derived["driver_diameter_m"] = (
            "2*sqrt(Sd_cm2*1e-4/pi) from driver_ts YAML (not printed as a diameter)")
    else:
        refusals["driver_diameter_m"] = GEOMETRY_FIELD_UNAVAILABLE

    for bl_field, yaml_field in (
        ("cone_depth_m", "cone_depth_mm"),
        ("surround_width_m", "surround_width_mm"),
        ("cap_diameter_m", "dust_cap_diameter_mm"),
    ):
        value = _number(geo_data, yaml_field)
        if value is None:
            refusals[bl_field] = GEOMETRY_FIELD_UNAVAILABLE
        else:
            values[bl_field] = round(value / 1000.0, 15)
            derived[bl_field] = f"{yaml_field}/1000 from geometry YAML (mm -> m)"

    # driver_y is a placement decision on the front baffle; the geometry schema has no such key.
    refusals["driver_y_m"] = GEOMETRY_FIELD_UNAVAILABLE

    return GeometryOverrides(
        driver_id=str(geo_data.get("driver_id") or geometry_path.stem),
        geometry_path=str(geometry_path),
        geometry_sha256=_sha256_file(geometry_path),
        values=values,
        refusals=refusals,
        present_fields=present,
        derived=derived,
    )


def _port_outer_m(point: BoxPoint, *, port_roundover_m: float, port_wall_m: float) -> float:
    area_m2 = float(point.port_throat_area_cm2) * 1e-4
    if not (math.isfinite(area_m2) and area_m2 > 0.0):
        raise ValueError("port throat area must be finite and > 0")
    throat = math.sqrt(area_m2 / math.pi)
    return throat + float(port_roundover_m) + float(port_wall_m)


def panel_placement(
    point: BoxPoint,
    driver_diameter_m: float,
    *,
    port_roundover_m: float = 0.008,
    port_wall_m: float = 0.003,
    clearance_m: float = BL_VALIDATE_CLEARANCE_M,
) -> dict[str, Any]:
    """Widest legal driver/port ``y`` placement on the baffle, mirroring BL validate L100-109.

    This is only a *source placement* derivation (BL's own validator still runs inside the
    provider). For each component the maximum legal ``|y|`` is
    ``half_height - radius - clearance``; the driver sits positive and the port negative, which
    maximises their separation. Reported values are authoritative only once BL accepts them.
    """
    half_h = float(point.external_height_mm) / 2000.0 - float(point.wall_mm) / 1000.0
    half_w = float(point.external_width_mm) / 2000.0 - float(point.wall_mm) / 1000.0
    driver_r = float(driver_diameter_m) / 2.0
    port_outer = _port_outer_m(point, port_roundover_m=port_roundover_m, port_wall_m=port_wall_m)
    eps = 1e-12
    driver_y = half_h - driver_r - clearance_m - eps
    port_y = -(half_h - port_outer - clearance_m - eps)
    required_sep = driver_r + port_outer + clearance_m
    available_sep = driver_y - port_y
    return {
        "driver_y_m": driver_y,
        "port_y_m": port_y,
        "driver_radius_m": driver_r,
        "port_outer_radius_m": port_outer,
        "required_separation_m": required_sep,
        "available_separation_m": available_sep,
        "driver_fits_wall": driver_r + clearance_m < half_w and abs(driver_y) + driver_r + clearance_m < half_h,
        "port_fits_wall": port_outer + clearance_m < half_w and abs(port_y) + port_outer + clearance_m < half_h,
        "separation_ok": available_sep > required_sep,
        "clearance_m": clearance_m,
        "source": ("BL parameters.py::validate lines 100-109; same max-legal-y convention as "
                   "hornlab_search.system.woofer_seed._bl_panel_fit_for_screen"),
    }


# --------------------------------------------------------------------------- seed box / source

@dataclass(frozen=True)
class SeedReference:
    """The committed panel-fit seed row used as the enclosure reference."""

    point: BoxPoint
    candidate_id: str
    driver_id: str
    placement: Mapping[str, Any]
    source_path: str
    source_sha256: str
    net_volume_l: float
    port_throat_area_cm2: float


def load_seed_reference_box(
    path: str | Path = SEED_PATH,
    candidate_id: str = SEED_CANDIDATE_ID,
) -> SeedReference:
    """Read the exact committed box row (no re-derivation of box dimensions)."""
    seed_path = Path(path)
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    rows = payload.get("kept_rows")
    if not isinstance(rows, list):
        raise ValueError(f"{seed_path} has no kept_rows list")
    row = next((item for item in rows if item.get("candidate_id") == candidate_id), None)
    if row is None:
        raise ValueError(f"candidate {candidate_id!r} not found in {seed_path}")
    box = row.get("box") or {}
    if box.get("kind") != "vented":
        raise ValueError(f"candidate {candidate_id!r} is not a vented box")
    area_cm2 = float(box["port_throat_area_cm2"])
    tuning = float(box["derived_tuning_hz"])
    net_l = float(box["net_volume_l"])
    l_eff = bass_reference.bassbox.port_effective_length(
        net_l * 1e-3, tuning, area_cm2 * 1e-4)
    point = BoxPoint(
        kind="vented",
        external_width_mm=float(box["external_width_mm"]),
        external_height_mm=float(box["external_height_mm"]),
        external_depth_mm=float(box["external_depth_mm"]),
        net_volume_l=net_l,
        wall_mm=float(box["wall_mm"]),
        port_type=str(box["port_type"]),
        port_throat_area_cm2=area_cm2,
        # LF-tier convention (bass_reference: port_nfr is ignored; BL source uses the
        # straight-port profile, exactly as the committed panel-fit pre-check did).
        port_nfr=0.0,
        requested_tuning_hz=tuning,
        derived_effective_port_length_m=float(l_eff),
        derived_tuning_hz=tuning,
        fits=dict(row.get("feasibility") or {}),
    )
    return SeedReference(
        point=point,
        candidate_id=candidate_id,
        driver_id=str(row.get("driver_id")),
        placement=dict(row.get("placement") or {}),
        source_path=str(seed_path),
        source_sha256=_sha256_file(seed_path),
        net_volume_l=net_l,
        port_throat_area_cm2=area_cm2,
    )


def vented_source(
    point: BoxPoint,
    *,
    defaults: Mapping[str, float],
    driver_diameter_m: float,
    driver_y_m: float,
    port_y_m: float,
    port_nfr: float = 0.0,
    port_roundover_m: float | None = None,
    port_wall_m: float | None = None,
    mesh_size_m: float | None = None,
    detail_size_m: float | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """BL vented-enclosure source derived from the committed box + BL defaults.

    Box dimensions/tuning/area come from the seed row. Port length is the existing repo
    derivation (``bassbox.port_effective_length`` -> neck -> total length incl. both lips),
    not a new model. Every key must already exist in the provider manifest defaults.
    """
    if point.kind != "vented":
        raise ValueError("only vented boxes have a BL port")
    lip = float(defaults["port_roundover_m"] if port_roundover_m is None else port_roundover_m)
    wall = float(defaults["port_wall_m"] if port_wall_m is None else port_wall_m)
    area_cm2 = float(point.port_throat_area_cm2)
    area_m2 = area_cm2 * 1e-4
    tuning = float(point.derived_tuning_hz or point.requested_tuning_hz)
    l_eff = point.derived_effective_port_length_m
    if l_eff is None:
        l_eff = bass_reference.bassbox.port_effective_length(
            float(point.net_volume_l) * 1e-3, tuning, area_m2)
    r_eq = math.sqrt(area_m2 / math.pi)
    neck_m = float(l_eff) - bass_reference.bassbox.N_END * 0.85 * r_eq
    if not (math.isfinite(neck_m) and neck_m > 0.0):
        raise ValueError(f"derived port neck must be > 0 m, got {neck_m!r}")
    port_length_m = neck_m + 2.0 * lip

    overrides = {
        "width_m": round(float(point.external_width_mm) / 1000.0, 15),
        "height_m": round(float(point.external_height_mm) / 1000.0, 15),
        "depth_m": round(float(point.external_depth_mm) / 1000.0, 15),
        "wall_m": round(float(point.wall_mm) / 1000.0, 15),
        "driver_diameter_m": float(driver_diameter_m),
        "driver_y_m": float(driver_y_m),
        "port_length_m": port_length_m,
        "port_area_m2": area_m2,
        "port_nfr": float(port_nfr),
        "port_roundover_m": lip,
        "port_wall_m": wall,
        "port_y_m": float(port_y_m),
    }
    if mesh_size_m is not None:
        overrides["mesh_size_m"] = float(mesh_size_m)
    if detail_size_m is not None:
        overrides["detail_size_m"] = float(detail_size_m)

    source = {str(key): float(value) for key, value in defaults.items()}
    unknown = set(overrides) - set(source)
    if unknown:
        raise ValueError(f"not provider-manifest source keys: {sorted(unknown)}")
    source.update(overrides)
    record = {
        "box_source": "system_runs/woofer_seed_stage5_blfit/woofer_seed.json",
        "candidate_id": SEED_CANDIDATE_ID,
        "net_volume_l": float(point.net_volume_l),
        "port_throat_area_cm2": area_cm2,
        "tuning_hz": tuning,
        "derived_effective_port_length_m": float(l_eff),
        "port_neck_m": neck_m,
        "port_length_m": port_length_m,
        "port_nfr": float(port_nfr),
        "port_roundover_m": lip,
        "port_wall_m": wall,
        "port_nfr_convention": (
            "0.0 straight-port LF-tier convention used by the committed BL panel-fit pre-check; "
            "bass_reference ignores nfr at this tier"),
        "driver_diameter_m": float(driver_diameter_m),
        "driver_y_m": float(driver_y_m),
        "port_y_m": float(port_y_m),
    }
    return source, record


# --------------------------------------------------------------------------- staging spec

def runner_path() -> Path:
    return Path(__file__).with_name("runner_motor_stage.py")


def _provider_root(root: BLRoot) -> str:
    if not root.provider_dir:
        raise BLCapabilityError(("verified BLRoot has no provider directory",))
    path = Path(root.provider_dir)
    return str(path.parent if path.name == "vented_enclosure" else path)


def _require_verified(root: BLRoot) -> None:
    if not root.verified:
        raise BLCapabilityError(
            (f"BLRoot at {root.path} is not verified: " + " | ".join(root.missing),))


def _provider_defaults(root: BLRoot) -> dict[str, float]:
    manifest = root.detail.get("provider_manifest", {})
    defaults = manifest.get("default_source")
    if not isinstance(defaults, dict) or not defaults:
        raise BLCapabilityError(
            (f"{root.path} provider manifest has no usable default_source",))
    return {str(key): float(value) for key, value in defaults.items()}


def _merge_source(defaults: Mapping[str, float], overrides: Mapping[str, float]) -> dict[str, float]:
    unknown = set(overrides) - set(defaults)
    if unknown:
        raise ValueError(f"unknown vented-source key(s): {sorted(unknown)}")
    source = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"vented-source key {key!r} must be numeric")
        source[str(key)] = float(value)
    return source


def build_motor_stage_spec(
    root: BLRoot,
    *,
    case_dir: str | Path,
    document_id: str = EXPERIMENT_ID,
    document_name: str = "FaitalPRO 12PR300 reference",
    mesh_name: str = "vented",
    case_name: str = EXPERIMENT_ID,
    mapping: MotorMapping | None = None,
    geometry: GeometryOverrides | None = None,
    seed: SeedReference | None = None,
) -> dict[str, Any]:
    """Build the BL-side spec for one real-motor staging run (pure; no execution).

    The staged transducer *shape* is BL's provider default when the committed geometry YAML
    lacks the moving-surface fields; that limitation is recorded explicitly with
    :data:`MOTOR_GEOMETRY_INCOMPLETE` and the per-field tokens. The motor parameters are the
    committed real T/S values and do not depend on geometry.
    """
    _require_verified(root)
    defaults = _provider_defaults(root)
    mapping = mapping or map_motor()
    geometry = geometry or geometry_overrides()
    seed = seed or load_seed_reference_box()
    if not mapping.ok:
        raise ValueError(
            "motor mapping is incomplete; refusing to stage: "
            + json.dumps(dict(mapping.refusals), sort_keys=True))

    staged_diameter = float(defaults["driver_diameter_m"])
    placement = panel_placement(
        seed.point,
        staged_diameter,
        port_roundover_m=float(defaults["port_roundover_m"]),
        port_wall_m=float(defaults["port_wall_m"]),
    )
    if not (placement["driver_fits_wall"] and placement["port_fits_wall"]
            and placement["separation_ok"]):
        raise ValueError(
            "BL provider defaults do not fit the committed panel; refusing to guess a driver "
            f"placement: {json.dumps(placement, sort_keys=True)}")
    source, source_record = vented_source(
        seed.point,
        defaults=defaults,
        driver_diameter_m=staged_diameter,
        driver_y_m=placement["driver_y_m"],
        port_y_m=placement["port_y_m"],
    )

    geometry_attempt = None
    real_diameter = geometry.values.get("driver_diameter_m")
    if real_diameter is not None:
        real_placement = panel_placement(
            seed.point,
            float(real_diameter),
            port_roundover_m=float(defaults["port_roundover_m"]),
            port_wall_m=float(defaults["port_wall_m"]),
        )
        real_source, _ = vented_source(
            seed.point,
            defaults=defaults,
            driver_diameter_m=float(real_diameter),
            driver_y_m=real_placement["driver_y_m"],
            port_y_m=real_placement["port_y_m"],
        )
        geometry_attempt = {
            "label": "real_driver_diameter_only",
            "source": real_source,
            "placement": real_placement,
            "note": ("real Sd-derived moving diameter on the committed panel; cone depth / "
                     "surround / cap remain BL defaults because the geometry YAML refuses them"),
        }

    staged_transducer_refusals = {
        key: GEOMETRY_FIELD_UNAVAILABLE for key in geometry.refusals
    }
    staged_transducer_refusals["staged_transducer_shape"] = MOTOR_GEOMETRY_INCOMPLETE

    spec = {
        "case_dir": str(case_dir),
        "provider_root": _provider_root(root),
        "provider_dir": str(root.provider_dir),
        "provider_id": str(root.detail["provider_manifest"]["id"]),
        "source": _merge_source(defaults, source),
        "document_id": str(document_id),
        "document_name": str(document_name),
        "mesh_name": str(mesh_name),
        "case_name": str(case_name),
        "configuration": {"symmetry_config": {"mode": "off"}},
        "component_id": f"{document_id}/driver",
        "component_parameters": dict(mapping.parameters),
        "expectations": {
            **{key: float(mapping.parameters[key]) for key in (
                "re_ohm", "le_h", "bl_n_per_a", "mmd_kg", "cms_m_per_n", "rms_n_s_per_m")},
            "motion_profile": mapping.parameters["motion_profile"],
            "motion_axis": list(mapping.parameters["motion_axis"]),
        },
        "preferences": {
            "freq_min_hz": 30.0,
            "freq_max_hz": 100.0,
            "freq_count": 3,
            "observation_distance_m": 2.0,
            "polar_angle_step_deg": 90.0,
        },
        "mapping": mapping.to_record(),
        "geometry": geometry.to_record(),
        "geometry_overrides_used": staged_transducer_refusals,
        "geometry_attempt": geometry_attempt,
        "seed": {
            "source_path": seed.source_path,
            "source_sha256": seed.source_sha256,
            "candidate_id": seed.candidate_id,
            "driver_id": seed.driver_id,
            "placement": dict(seed.placement),
            "source_record": source_record,
        },
        "runner_version": "motor-v1",
    }
    return spec


# --------------------------------------------------------------------------- execution

@dataclass(frozen=True)
class MotorStagedProject:
    """Verified artifacts of one real-motor staging case."""

    ok: bool
    case_dir: Path
    project_path: Path | None
    output_dir: Path | None
    validation: bl_run.ValidationResult | None
    manifest_path: Path | None
    captured_log_tail: tuple[str, ...]
    returncode: int
    detail: Mapping[str, object] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        parsed = None if self.validation is None else self.validation.parsed
        return bool(
            self.ok
            and self.validation is not None
            and self.validation.returncode == 0
            and isinstance(parsed, dict)
            and parsed.get("valid") is True
        )


def _dependency_hashes(root: BLRoot) -> dict[str, str | None]:
    base = Path(root.path)
    return {
        relative: (provenance.file_sha256(base / relative) if (base / relative).is_file() else None)
        for relative in _MOTOR_STAGE_DEPENDENCIES
    }


def _validate_dict(result: bl_run.ValidationResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "returncode": result.returncode,
        "valid": None if result.parsed is None else result.parsed.get("valid"),
        "parsed": None if result.parsed is None else dict(result.parsed),
        "stdout_tail": list(result.stdout_tail[-12:]),
        "stderr_tail": list(result.stderr_tail[-12:]),
        "argv": list(result.argv),
    }


def stage_motor_project(
    root: BLRoot,
    *,
    store_root: str | Path | None = None,
    case_dir: Path | None = None,
    experiment_id: str = EXPERIMENT_ID,
    tag: str = "motor12pr",
    timeout_s: float = 1800.0,
    run_now: bool = True,
) -> MotorStagedProject:
    """Stage one vented project with the real committed motor through BL's patch API."""
    _require_verified(root)
    resolved = (Path(case_dir) if case_dir is not None else
                provenance.new_case_dir(experiment_id, store_root=store_root, tag=tag))
    mapping = map_motor()
    geometry = geometry_overrides()
    seed = load_seed_reference_box()
    spec = build_motor_stage_spec(
        root, case_dir=resolved, mapping=mapping, geometry=geometry, seed=seed)
    if not run_now:
        return MotorStagedProject(
            ok=False, case_dir=resolved, project_path=None, output_dir=None, validation=None,
            manifest_path=None, captured_log_tail=(), returncode=-1,
            detail={"spec_dry_run": spec})
    resolved.mkdir(parents=True, exist_ok=True)
    spec_path = resolved / "adapter_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")

    python = root.python_executable
    if not python:
        raise BLCapabilityError(("verified BLRoot has no python executable",))
    argv = [python, "-I", "-B", str(runner_path()), str(spec_path)]
    code, log_lines = _execute(argv, timeout_s, None)
    final = _parse_final_json(log_lines)
    staged = code == 0 and final is not None and final.get("ok") is True
    project_path = Path(final["project_path"]) if staged and final else None
    validation = None
    if staged and project_path is not None:
        if not project_path.is_file():
            staged = False
            log_lines.append(f"[adapter] verification failed: project file missing: {project_path}")
        else:
            validation = bl_run.validate_project(root, project_path)
            if validation.returncode != 0 or not (validation.parsed or {}).get("valid"):
                staged = False
                log_lines.append(
                    "[adapter] blab project validate rejected the staged project: rc="
                    f"{validation.returncode} parsed="
                    f"{json.dumps(validation.parsed or {}, sort_keys=True)}")

    patch = mapping.patch(spec["document_id"])
    manifest_payload: dict[str, Any] = {
        "kind": "bl_motor_stage_project",
        "experiment_id": experiment_id,
        "bl_root": root.to_dict(),
        "bl_dependency_hashes": _dependency_hashes(root),
        "runner": str(runner_path()),
        "runner_sha256": provenance.file_sha256(runner_path()),
        "spec": spec,
        "spec_sha256": provenance.file_sha256(spec_path),
        "motor_mapping": mapping.to_record(),
        "geometry_overrides": geometry.to_record(),
        "yaml_sha256": {
            "driver_ts": mapping.ts_sha256,
            "driver_geometry": geometry.geometry_sha256,
        },
        "configuration_patch": patch,
        "configuration_patch_sha256": hashlib.sha256(
            canonical_json(patch).encode()).hexdigest(),
        "result": final,
        "validate": _validate_dict(validation),
    }
    if staged and project_path is not None:
        manifest_payload["project_sha256"] = provenance.file_sha256(project_path)
    manifest_path = provenance.write_manifest(resolved, manifest_payload)
    output_dir = Path(final["output_dir"]) if final and final.get("output_dir") else None
    return MotorStagedProject(
        ok=staged,
        case_dir=resolved,
        project_path=project_path,
        output_dir=output_dir,
        validation=validation,
        manifest_path=manifest_path,
        captured_log_tail=tuple(log_lines[-_MAX_LOG_LINES:]),
        returncode=code,
        detail={
            "argv": argv,
            "spec_sha256": provenance.file_sha256(spec_path),
            "patch": patch,
            "patch_sha256": manifest_payload["configuration_patch_sha256"],
        },
    )
