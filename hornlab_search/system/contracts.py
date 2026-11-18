"""Additive contracts for the ``hornlab_search.system`` package.

A modular horn + vented-woofer two-way system layer (feat/woofer-system-v0).
This file is NEW and strictly additive: it changes no frozen contract. ``hornlab_search/types.py``,
``docs/plan/01_CONTRACTS.md``, the v9 horn objective and every existing run-cache format are
untouched by this module. Everything in this file is a new, versioned system contract.

Canonical conventions (frozen for this package)
-----------------------------------------------
* **Time convention:** ``exp(+j omega t)`` everywhere. This matches
  ``hornlab_search.meh.network`` / ``meh.dsp`` and ``tools/bassbox.py``. Complex fields imported
  from a HornFab isolated-horn solve must be converted at the import boundary (unit normal
  acceleration, ``exp(-j omega t)`` -> velocity-normalised ``exp(+j omega t)``, the
  ``compare/hornfab_side.py`` direction) and carry their conversion record in provenance.
* **Quantity and unit:** pressure, Pa, RMS phasors.
* **Normalisation:** a complex basis field is per input unit as declared in
  :attr:`SourceBasis.per_input`: ``"V_rms"`` (electrodynamic sources) or
  ``"normal_velocity_mps"`` (ideal prescribed-velocity sources).
* **Bases:** every complex field carries a :class:`SourceBasis`. A coherent multi-source
  combination requires equal time convention, quantity, per-input normalisation *and* a declared
  observation frame; the physical propagation phase factor may be applied at most once (it is
  already inside fields evaluated with all sources in one global coordinate frame).
* **Phase honesty:** a magnitude-only asset may take part in level-only screening. It can never
  take part in phase-sensitive combination, delay optimisation, or any claimed acoustic
  crossover: code raises :class:`PhaseUnavailable` instead of imputing phase.
* **Fidelity labels:** numbers are comparable only within one declared fidelity level *and* one
  ``system_objective_version``. Never compare across fidelity levels as if one metric.
* **Identity:** domain-separated SHA-256 identities; an existing horn
  ``physical_solve_id`` / ``score_id`` is never reused as a system identity.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping, cast

import numpy as np

from hornlab_search.meh.drivers import ConeDriver

__all__ = [
    "SCHEMA_VERSION", "TIME_CONVENTION", "SYSTEM_OBJECTIVE_VERSION",
    "AssetQuality", "Fidelity", "SystemMode", "SpecFidelity", "StatusToken",
    "PhaseUnavailable", "IncompatibleBasis", "SchemaError", "DataQualityError",
    "SourceBasis", "GeometryMetadata", "HornAsset",
    "DriverGeometry", "WooferDriver",
    "VentedBoxRanges", "BoxPoint", "AssemblyRanges", "AssemblyPoint",
    "DspRanges", "DspPoint", "SystemTargets", "HornRef", "WooferRef",
    "SystemSpecV1", "parse_system_spec_dict", "SCHEMA_V1_KEYS", "SCHEMA_V1_SUBKEYS",
    "SystemResponse",
    "canonical_json", "domain_sha16",
    "assembly_geometry_id", "system_physics_id", "system_analysis_id",
    "system_score_id", "system_study_id", "system_objective_id",
    "validate_finite_range", "REPORT_AXES",
]


# --------------------------------------------------------------------------- frozen constants

#: The only schema version this module accepts.
SCHEMA_VERSION = 1
#: The only time convention this package supports.
TIME_CONVENTION = "exp(+jomega_t)"
#: The only system objective version in this branch (v9 horn objective stays untouched).
SYSTEM_OBJECTIVE_VERSION = 1

AssetQuality = Literal[
    "EXACT_COMPLEX", "MAGNITUDE_ONLY", "GEOMETRY_ONLY", "STALE_SOURCE", "INCOMPATIBLE"
]
Fidelity = Literal[
    "SCREEN_MAGNITUDE", "SCREEN_COMPLEX_APPROX",
    "INSTALLED_EXTERIOR_BEM", "COUPLED_VENTED_FEM_BEM_LEM",
    "MEASURED_VALIDATED",
]
SystemMode = Literal["fixed_horn", "horn_portfolio"]
SpecFidelity = Literal["screen_only", "reference"]
SystemAxis = Literal[
    "feasible_construction", "lf_headroom", "crossover_physics",
    "angular_field", "practical_sound", "robustness", "cost_size",
]
#: Report-only axes available before any scalar objective is authorised.
REPORT_AXES: tuple[str, ...] = (
    "feasible_construction", "lf_headroom", "crossover_physics",
    "angular_field", "practical_sound", "robustness", "cost_size",
)

#: Status tokens used in reports (no unit semantics; labelling only).
StatusToken = Literal["PASS", "FAIL", "SCREEN_ONLY", "REFUSED", "BLOCKED", "PHASE_UNAVAILABLE"]


# --------------------------------------------------------------------------- errors

class PhaseUnavailable(ValueError):
    """A magnitude-only asset was asked to take part in a phase-sensitive claim."""


class IncompatibleBasis(ValueError):
    """Two basis fields cannot be coherently combined."""


class SchemaError(ValueError):
    """A system spec/manifest does not satisfy this module's schema."""


class DataQualityError(ValueError):
    """An asset or driver is too incomplete for the requested claim."""


def require(condition: bool, message: str, error: type[Exception] = ValueError) -> None:
    if not condition:
        raise error(message)


# --------------------------------------------------------------------------- source basis

@dataclass(frozen=True)
class SourceBasis:
    """The normalisation/frame declaration of a complex acoustic field.

    ``per_input`` is the physical input the pressure is normalised to:
    ``"V_rms"`` for an electrodynamic source (Pa per rms volt at the source terminals)
    or ``"normal_velocity_mps"`` for an ideal prescribed-velocity surface (Pa per m/s).
    ``distance_m`` is the reference distance of the field (far-field reference if declared).
    ``origin_xyz_m`` is the coordinate origin of the observation frame, metres.
    ``angular_frame`` names the sampling frame: ``"hornfab_cuts_hv"`` (H/V angle grids),
    ``"cartesian_dirs"`` (unit direction vectors) or ``"unknown"``.
    """

    per_input: Literal["V_rms", "normal_velocity_mps"]
    time_convention: str = TIME_CONVENTION
    quantity: Literal["pressure_pa"] = "pressure_pa"
    distance_m: float | None = None
    origin_xyz_m: tuple[float, float, float] | None = None
    angular_frame: str = "unknown"
    source_geometry_hash: str | None = None

    def __post_init__(self) -> None:
        require(self.time_convention == TIME_CONVENTION,
                f"system basis requires time convention {TIME_CONVENTION!r}, "
                f"got {self.time_convention!r}", IncompatibleBasis)
        require(self.per_input in ("V_rms", "normal_velocity_mps"),
                f"per_input must be 'V_rms' or 'normal_velocity_mps', got {self.per_input!r}",
                IncompatibleBasis)
        if self.distance_m is not None:
            require(math.isfinite(self.distance_m) and self.distance_m > 0.0,
                    f"distance_m must be finite and > 0, got {self.distance_m!r}", IncompatibleBasis)

    def compatible_for_sum_with(self, other: "SourceBasis") -> tuple[bool, str]:
        """Whether two independent-source fields may be coherently summed as stored.

        Equality is required in time convention, quantity and per-input normalisation.
        Distances/origins may differ ONLY if a geometric phase/spatial factor is explicitly
        applied by the combiner; returning False here is the conservative default whenever the
        field metadata does not prove a single shared observation frame.
        """
        if self.time_convention != other.time_convention:
            return False, f"time convention {self.time_convention!r} vs {other.time_convention!r}"
        if self.quantity != other.quantity:
            return False, f"quantity {self.quantity!r} vs {other.quantity!r}"
        if self.per_input != other.per_input:
            return False, f"per_input {self.per_input!r} vs {other.per_input!r}"
        if self.distance_m is None or other.distance_m is None:
            return False, "missing distance declaration on at least one field"
        if self.angular_frame != other.angular_frame:
            return False, f"angular frame {self.angular_frame!r} vs {other.angular_frame!r}"
        if not (self.origin_xyz_m and other.origin_xyz_m):
            return False, "observation origin not declared on both fields"
        if not (self.source_geometry_hash and other.source_geometry_hash):
            return False, "source geometry hash missing on at least one field"
        return True, "declared compatible"


# --------------------------------------------------------------------------- horn asset

@dataclass(frozen=True)
class GeometryMetadata:
    """Provenance metadata for one saved horn solve (read-only view)."""

    family: str | None = None
    brief_id: str | None = None
    physical_solve_id: str | None = None
    analysis_id: str | None = None
    score_id: str | None = None
    objective_version: str | None = None
    mesh_sha256: str | None = None
    run_dir: str | None = None
    band_hz: tuple[float, float] | None = None
    source_urls: tuple[str, ...] = ()
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HornAsset:
    """One read-only saved horn response, qualified for (or rejected from) system use."""

    asset_id: str
    design_hash: str
    response_path: str
    mesh_path: str | None
    geometry: GeometryMetadata
    available_fields: frozenset[str]
    quality: Literal["EXACT_COMPLEX", "MAGNITUDE_ONLY", "GEOMETRY_ONLY",
                     "STALE_SOURCE", "INCOMPATIBLE"]
    freqs_hz: tuple[float, ...]
    source_basis: SourceBasis | None

    def __post_init__(self) -> None:
        require(bool(self.asset_id and self.design_hash and self.response_path),
                "HornAsset needs asset_id, design_hash and response_path", DataQualityError)
        if self.quality == "EXACT_COMPLEX":
            require(self.source_basis is not None,
                    "EXACT_COMPLEX asset must declare a SourceBasis", DataQualityError)

    @property
    def has_complex(self) -> bool:
        return bool({"p_h", "p_v", "p_balloon"} & set(self.available_fields))

    def require_complex(self) -> SourceBasis:
        """Phase gate: what a phase-sensitive claim needs, raised instead of imputed."""
        if self.quality != "EXACT_COMPLEX" or self.source_basis is None:
            raise PhaseUnavailable(
                f"asset {self.asset_id!r} is {self.quality!r}; no complex polar data. "
                "Level-only screening remains allowed: report MAGNITUDE_ONLY / "
                "PHASE_ALIGNMENT_UNAVAILABLE and suppress delay/coherent claims.")
        if not self.has_complex:
            raise PhaseUnavailable(
                f"asset {self.asset_id!r} declares quality EXACT_COMPLEX but its field set "
                f"{sorted(self.available_fields)} has no p_* complex field")
        return self.source_basis


# --------------------------------------------------------------------------- woofer driver

@dataclass(frozen=True)
class DriverGeometry:
    """Measured/maker geometry needed for an INSTALLED moving-surface model.

    All lengths mm, areas cm2. Any None means "not known" — the caller must refuse
    installed-boundary claims that need the missing piece instead of inventing it.
    """

    cutout_mm: float | None = None
    frame_od_mm: float | None = None
    depth_mm: float | None = None
    cone_depth_mm: float | None = None
    surround_width_mm: float | None = None
    dust_cap_diameter_mm: float | None = None
    mounting_depth_behind_baffle_mm: float | None = None
    source_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class WooferDriver:
    """One real, sourced cone woofer: T/S via ConeDriver + geometry + provenance.

    ``cone`` is an existing ``hornlab_search.meh.drivers.ConeDriver`` (unchanged, reused).
    ``data_quality`` records which datasheet fields were available; missing precision inputs
    forbid precision absolute-level claims.
    """

    driver_id: str
    cone: ConeDriver
    geometry_mm: DriverGeometry | None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    data_quality: Mapping[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(bool(self.driver_id), "WooferDriver needs driver_id", DataQualityError)
        require(bool(self.cone.source),
                f"driver {self.driver_id!r}: ConeDriver must carry a datasheet source URL",
                DataQualityError)

    def require_geometry(self) -> DriverGeometry:
        if self.geometry_mm is None:
            raise DataQualityError(
                f"driver {self.driver_id!r} has no geometry: BL installed moving-surface "
                "fidelity is refused; T/S-only low-fidelity screening is still allowed")
        return self.geometry_mm


# --------------------------------------------------------------------------- boxes, assembly, dsp

@dataclass(frozen=True)
class VentedBoxRanges:
    """Enclosure search ranges. External dims mm, volumes L, tuning Hz, port areas cm2.

    Fb is an OUTCOME of net volume, port effective length and area — never an independent
    input mixed with length; the optimizer derives a feasible length from (Vb, fb request,
    area) or searches geometry directly and reports the resulting fb.
    """

    kind: Literal["vented", "sealed"] = "vented"
    external_width_mm_range: tuple[float, float] = (340.0, 510.0)
    external_height_mm_range: tuple[float, float] = (470.0, 850.0)
    external_depth_mm_range: tuple[float, float] = (260.0, 570.0)
    net_volume_l_range: tuple[float, float] = (35.0, 115.0)
    tuning_hz_range: tuple[float, float] = (30.0, 65.0)
    wall_mm: float = 18.0
    port_type: Literal["round_flared", "round_straight", "slot"] = "round_flared"
    port_throat_area_cm2_range: tuple[float, float] = (45.0, 170.0)
    port_nfr_range: tuple[float, float] = (0.0, 0.2)

    def validate(self) -> None:
        require(self.kind in ("vented", "sealed"), f"box kind must be 'vented'|'sealed', "
                f"got {self.kind!r}", SchemaError)
        require(self.port_type in ("round_flared", "round_straight", "slot"),
                f"port_type must be 'round_flared'|'round_straight'|'slot', got {self.port_type!r}",
                SchemaError)
        validate_finite_range("external_width_mm", *self.external_width_mm_range)
        validate_finite_range("external_height_mm", *self.external_height_mm_range)
        validate_finite_range("external_depth_mm", *self.external_depth_mm_range)
        validate_finite_range("net_volume_l", *self.net_volume_l_range)
        validate_finite_range("tuning_hz", *self.tuning_hz_range)
        validate_finite_range("port_throat_area_cm2", *self.port_throat_area_cm2_range)
        validate_finite_range("port_nfr", *self.port_nfr_range)


@dataclass(frozen=True)
class BoxPoint:
    """One resolved feasible enclosure (the optimizer's output, all values concrete)."""

    kind: Literal["vented", "sealed"]
    external_width_mm: float
    external_height_mm: float
    external_depth_mm: float
    net_volume_l: float
    wall_mm: float
    port_type: str
    port_throat_area_cm2: float
    port_nfr: float
    requested_tuning_hz: float
    derived_effective_port_length_m: float | None = None
    derived_tuning_hz: float | None = None
    fits: Mapping[str, Any] = field(default_factory=dict)  # feasibility flags/reasons


@dataclass(frozen=True)
class AssemblyRanges:
    """Placement ranges: woofer centre offsets on the front baffle, horn mount offsets.

    mm, in the cabinet-front coordinate frame (z = 0 baffle, forward = +z away from the box).
    """

    horn_layout: Literal["separate_above", "separate_side_baffle", "flush_baffle"] = "separate_above"
    woofer_center_y_mm_range: tuple[float, float] = (90.0, 400.0)
    woofer_center_x_mm_range: tuple[float, float] = (0.0, 0.0)
    horn_mounting_offset_z_mm_range: tuple[float, float] = (-80.0, 80.0)

    def validate(self) -> None:
        require(self.horn_layout in ("separate_above", "separate_side_baffle", "flush_baffle"),
                f"horn_layout must be 'separate_above'|'separate_side_baffle'|'flush_baffle', "
                f"got {self.horn_layout!r}", SchemaError)
        validate_finite_range("woofer_center_y_mm", *self.woofer_center_y_mm_range)
        validate_finite_range("woofer_center_x_mm", *self.woofer_center_x_mm_range)
        validate_finite_range("horn_mounting_offset_z_mm", *self.horn_mounting_offset_z_mm_range)


@dataclass(frozen=True)
class AssemblyPoint:
    """One resolved assembly: explicit transforms, never inferred from names."""

    horn_layout: str
    woofer_center_xyz_mm: tuple[float, float, float]
    horn_mount_offset_z_mm: float
    horn_mount_transform_m: tuple[tuple[float, ...], ...]   # 4x4 row-major, metres
    assembly_origin_description: str
    horn_to_woofer_center_sep_mm: float
    baffle_seam_model: Literal["separate_closed_meshes", "flush_seam_explicit"]


@dataclass(frozen=True)
class DspRanges:
    """Two-way active DSP search ranges (wraps meh/dsp.py blocks; no second implementation)."""

    active: bool = True
    xo_hz_range: tuple[float, float] = (700.0, 1300.0)
    crossover_types: tuple[str, ...] = ("LR4",)
    gain_db_range: tuple[float, float] = (-12.0, 0.0)
    relative_delay_ms_range: tuple[float, float] = (-1.5, 1.5)
    peq_max_bands: int = 2
    peq_max_boost_db: float = 3.0

    def validate(self) -> None:
        validate_finite_range("xo_hz", *self.xo_hz_range)
        validate_finite_range("gain_db", *self.gain_db_range)
        validate_finite_range("relative_delay_ms", *self.relative_delay_ms_range)
        require(all(t in ("LR2", "LR4", "LR8") for t in self.crossover_types),
                f"crossover_types must be LR2/LR4/LR8, got {self.crossover_types}",
                SchemaError)
        require(self.peq_max_bands >= 0, f"peq_max_bands >= 0, got {self.peq_max_bands}",
                SchemaError)


@dataclass(frozen=True)
class DspPoint:
    """One resolved DSP setting (complex analog prototype + honest delay).

    Channel conventions (verified against hornlab_search/system/dsp.py and meh/dsp.py):
    ``relative_delay_ms`` delays the HORN (positive = horn later), ``polarity_woofer`` and
    ``peq_bands_woofer`` act on the woofer only, and PEQ band tuples are
    ``(fc_hz, gain_db, Q)`` — gain before Q, matching ``meh/dsp.peaking(f, fc, gain_db, q)``.
    """

    crossover_type: str
    xo_hz: float
    gain_db_woofer: float
    gain_db_horn: float
    relative_delay_ms: float          # horn relative to woofer
    polarity_woofer: float            # +1 / -1
    peq_bands_woofer: tuple[tuple[float, float, float], ...] = ()


@dataclass(frozen=True)
class SystemTargets:
    """Coverage/size target the screening reports against (never silently widened)."""

    beamwidth_h_deg: tuple[float, float] | None = None
    beamwidth_v_deg: tuple[float, float] | None = None
    listening_angle_h_deg: tuple[float, float] = (-30.0, 30.0)
    listening_angle_v_deg: tuple[float, float] = (-15.0, 15.0)
    low_freq_f3_hz_max: float | None = None


@dataclass(frozen=True)
class HornRef:
    asset_id: str
    driver_profile_id: str | None = None


@dataclass(frozen=True)
class WooferRef:
    driver_id: str
    geometry_file: str | None = None


# --------------------------------------------------------------------------- spec v1

SCHEMA_V1_KEYS: frozenset[str] = frozenset({
    "schema_version", "experiment_id", "mode", "horn", "woofer",
    "cabinet", "assembly", "dsp", "target", "fidelity",
})
SCHEMA_V1_SUBKEYS: Mapping[str, frozenset[str]] = {
    "horn": frozenset({"asset_id", "driver_profile_id"}),
    "woofer": frozenset({"driver_id", "geometry_file"}),
    "cabinet": frozenset({
        "kind", "external_width_mm_range", "external_height_mm_range",
        "external_depth_mm_range", "net_volume_l_range", "tuning_hz_range",
        "wall_mm", "port_type", "port_throat_area_cm2_range", "port_nfr_range",
    }),
    "assembly": frozenset({
        "horn_layout", "woofer_center_y_mm_range", "woofer_center_x_mm_range",
        "horn_mounting_offset_z_mm_range",
    }),
    "dsp": frozenset({
        "active", "xo_hz_range", "crossover_types", "gain_db_range",
        "relative_delay_ms_range", "peq_max_bands", "peq_max_boost_db",
    }),
    "target": frozenset({
        "beamwidth_h_deg", "beamwidth_v_deg", "listening_angle_h_deg",
        "listening_angle_v_deg", "low_freq_f3_hz_max",
    }),
}


@dataclass(frozen=True)
class SystemSpecV1:
    """The frozen v1 system experiment spec (mode A pilot input; mode B reuses it per horn)."""

    experiment_id: str
    mode: SystemMode
    horn: HornRef
    woofer: WooferRef
    cabinet: VentedBoxRanges
    assembly: AssemblyRanges
    dsp: DspRanges
    target: SystemTargets
    fidelity: SpecFidelity

    def __post_init__(self) -> None:
        raise_dataclass_errors(self)

    def hash(self) -> str:
        return system_study_id(asdict(self))


def raise_dataclass_errors(spec: "SystemSpecV1") -> None:
    require(bool(spec.experiment_id), "experiment_id must be non-empty", SchemaError)
    require(spec.mode in ("fixed_horn", "horn_portfolio"),
            f"mode must be fixed_horn|horn_portfolio, got {spec.mode!r}", SchemaError)
    require(spec.fidelity in ("screen_only", "reference"),
            f"fidelity must be screen_only|reference, got {spec.fidelity!r}", SchemaError)
    spec.cabinet.validate()
    spec.assembly.validate()
    spec.dsp.validate()


def _get_pair(d: Mapping[str, Any], key: str, path: str) -> tuple[float, float]:
    v = d.get(key)
    if (not isinstance(v, (list, tuple))) or len(v) != 2:
        raise SchemaError(f"{path}.{key} must be a [lo, hi] pair, got {v!r}")
    return float(v[0]), float(v[1])


def _pair_or(d: Mapping[str, Any], key: str, path: str,
             default: tuple[float, float]) -> tuple[float, float]:
    """A range key falls back to its frozen default when absent; malformed pairs still error."""
    if d.get(key) is None:
        return default
    return _get_pair(d, key, path)


def parse_system_spec_dict(d: Mapping[str, Any]) -> SystemSpecV1:
    """Strict schema-v1 parser: unknown keys (anywhere), bad ranges and bad enums are errors."""
    if not isinstance(d, Mapping):
        raise SchemaError(f"spec must be a mapping, got {type(d).__name__}")
    if d.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"schema_version must be {SCHEMA_VERSION}, got {d.get('schema_version')!r}")
    unknown = set(d) - SCHEMA_V1_KEYS
    if unknown:
        raise SchemaError(f"unknown spec keys: {sorted(unknown)}")
    missing = SCHEMA_V1_KEYS - set(d)
    if missing:
        raise SchemaError(f"missing required spec keys: {sorted(missing)}")

    for name, allowed in SCHEMA_V1_SUBKEYS.items():
        sub = d[name]
        if not isinstance(sub, Mapping):
            raise SchemaError(f"{name} must be a mapping, got {type(sub).__name__}")
        bad = set(sub) - allowed
        if bad:
            raise SchemaError(f"unknown {name} keys: {sorted(bad)}")

    horn = d["horn"]
    woofer = d["woofer"]
    cab = d["cabinet"]
    asm = d["assembly"]
    dsp = d["dsp"]
    tgt = d["target"]

    cab_ranges = VentedBoxRanges(
        kind=cast(Literal["vented", "sealed"], str(cab.get("kind", "vented"))),
        external_width_mm_range=_pair_or(cab, "external_width_mm_range", "cabinet", (340.0, 510.0)),
        external_height_mm_range=_pair_or(cab, "external_height_mm_range", "cabinet",
                                          (470.0, 850.0)),
        external_depth_mm_range=_pair_or(cab, "external_depth_mm_range", "cabinet", (260.0, 570.0)),
        net_volume_l_range=_pair_or(cab, "net_volume_l_range", "cabinet", (35.0, 115.0)),
        tuning_hz_range=_pair_or(cab, "tuning_hz_range", "cabinet", (30.0, 65.0)),
        wall_mm=float(cab.get("wall_mm", 18.0)),
        port_type=cast(Literal["round_flared", "round_straight", "slot"],
                       str(cab.get("port_type", "round_flared"))),
        port_throat_area_cm2_range=_pair_or(cab, "port_throat_area_cm2_range", "cabinet",
                                            (45.0, 170.0)),
        port_nfr_range=_pair_or(cab, "port_nfr_range", "cabinet", (0.0, 0.2)),
    )
    asm_ranges = AssemblyRanges(
        horn_layout=cast(Literal["separate_above", "separate_side_baffle", "flush_baffle"],
                         str(asm.get("horn_layout", "separate_above"))),
        woofer_center_y_mm_range=_pair_or(asm, "woofer_center_y_mm_range", "assembly",
                                          (90.0, 400.0)),
        woofer_center_x_mm_range=_pair_or(asm, "woofer_center_x_mm_range", "assembly", (0.0, 0.0)),
        horn_mounting_offset_z_mm_range=_pair_or(asm, "horn_mounting_offset_z_mm_range", "assembly",
                                                 (-80.0, 80.0)),
    )
    dsp_ranges = DspRanges(
        active=bool(dsp.get("active", True)),
        xo_hz_range=_pair_or(dsp, "xo_hz_range", "dsp", (700.0, 1300.0)),
        crossover_types=tuple(str(t) for t in dsp.get("crossover_types", ("LR4",))),
        gain_db_range=_pair_or(dsp, "gain_db_range", "dsp", (-12.0, 0.0)),
        relative_delay_ms_range=_pair_or(dsp, "relative_delay_ms_range", "dsp", (-1.5, 1.5)),
        peq_max_bands=int(dsp.get("peq_max_bands", 2)),
        peq_max_boost_db=float(dsp.get("peq_max_boost_db", 3.0)),
    )
    bwh = tgt.get("beamwidth_h_deg")
    bwv = tgt.get("beamwidth_v_deg")
    targets = SystemTargets(
        beamwidth_h_deg=cast("tuple[float, float] | None",
                             None if bwh is None else tuple(float(x) for x in bwh)),
        beamwidth_v_deg=cast("tuple[float, float] | None",
                             None if bwv is None else tuple(float(x) for x in bwv)),
        listening_angle_h_deg=_get_pair(tgt, "listening_angle_h_deg", "target"),
        listening_angle_v_deg=_get_pair(tgt, "listening_angle_v_deg", "target"),
        low_freq_f3_hz_max=None if tgt.get("low_freq_f3_hz_max") is None
        else float(tgt["low_freq_f3_hz_max"]),
    )
    if tgt.get("listening_angle_h_deg") is None or tgt.get("listening_angle_v_deg") is None:
        raise SchemaError("target listening angles are required (listening_angle_h_deg/v_deg)")

    spec = SystemSpecV1(
        experiment_id=str(d["experiment_id"]),
        mode=cast(SystemMode, str(d["mode"])),
        horn=HornRef(asset_id=str(horn["asset_id"]),
                     driver_profile_id=(None if horn.get("driver_profile_id") is None
                                        else str(horn["driver_profile_id"]))),
        woofer=WooferRef(driver_id=str(woofer["driver_id"]),
                         geometry_file=(None if woofer.get("geometry_file") is None
                                        else str(woofer["geometry_file"]))),
        cabinet=cab_ranges,
        assembly=asm_ranges,
        dsp=dsp_ranges,
        target=targets,
        fidelity=cast(SpecFidelity, str(d["fidelity"])),
    )
    spec.__post_init__()
    return spec


def validate_finite_range(name: str, lo: float, hi: float) -> None:
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise SchemaError(f"{name} range must be finite, got [{lo!r}, {hi!r}]")
    if lo > hi:
        raise SchemaError(f"{name} range must be lo <= hi, got [{lo!r}, {hi!r}]")


# --------------------------------------------------------------------------- response

@dataclass
class SystemResponse:
    """The assembled linear response of one two-way system, at one fidelity level.

    ``p_by_excitation[excitation]`` is an ``(nf, nobs)`` complex128 array, Pa per the excitation's
    declared :class:`SourceBasis`. ``p_total`` is the coherent sum with applied DSP (only at a
    fidelity where coherent combination is declared valid). A magnitude-only response stores
    ``spline/magnitude_screen`` and MUST leave ``p_total`` None.
    """

    frequencies_hz: np.ndarray
    excitation_names: tuple[str, ...]
    p_by_excitation: Mapping[str, np.ndarray] | None
    excitation_bases: Mapping[str, SourceBasis]
    p_total: np.ndarray | None
    magnitude_screen: np.ndarray | None
    observation_directions: np.ndarray | None        # (nobs, 3) unit vectors when declared
    observation_angles_deg: tuple[str, ...] | None   # e.g. ("h_deg", "v_deg")
    fidelity: str
    physics_provenance: Mapping[str, Any] = field(default_factory=dict)
    data_quality: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(self.fidelity in
                ("SCREEN_MAGNITUDE", "SCREEN_COMPLEX_APPROX", "INSTALLED_EXTERIOR_BEM",
                 "COUPLED_VENTED_FEM_BEM_LEM", "MEASURED_VALIDATED"),
                f"unknown fidelity {self.fidelity!r}", DataQualityError)
        if self.p_by_excitation is not None:
            bases = dict(self.excitation_bases)
            missing = [x for x in self.excitation_names if x not in dict(self.p_by_excitation)]
            unbased = [x for x in self.excitation_names if x not in bases]
            require(not missing, f"p_by_excitation missing excitations {missing}", DataQualityError)
            require(not unbased, f"excitations without SourceBasis: {unbased}", DataQualityError)
            for name, arr in self.p_by_excitation.items():
                require(arr.shape[0] == self.frequencies_hz.shape[0],
                        f"excitation {name!r} frequency axis mismatch", DataQualityError)
        if self.p_total is not None:
            require(self.p_by_excitation is not None,
                    "a total coherent sum needs independent-excitation bases", DataQualityError)

    def require_phase(self) -> None:
        if self.p_by_excitation is None or not self.excitation_names:
            raise PhaseUnavailable(
                "SystemResponse has no complex multi-excitation fields; "
                "coherent sum / delay claims are refused")


# --------------------------------------------------------------------------- identity

def canonical_json(obj: Any) -> str:
    """Stable JSON for hashing (sorted keys; floats rounded to 12 significant round-trips)."""
    def _fix(o: Any) -> Any:
        if isinstance(o, bool):
            return o
        if isinstance(o, (int, float)) and not isinstance(o, bool):
            return round(float(o), 12)
        if isinstance(o, Mapping):
            return {k: _fix(v) for k, v in sorted(o.items())}
        if isinstance(o, (list, tuple)):
            return [_fix(v) for v in o]
        if isinstance(o, np.ndarray):
            return _fix(o.tolist())
        return str(o)
    return json.dumps(_fix(obj), sort_keys=True, separators=(",", ":"))


def domain_sha16(domain: str, payload: Mapping[str, Any] | str) -> str:
    """Domain-separated 16-hex identity. Never reuse a horn score_id as a system id."""
    blob = canonical_json(payload) if not isinstance(payload, str) else payload
    return hashlib.sha256(f"{domain}|{blob}".encode()).hexdigest()[:16]


def assembly_geometry_id(payload: Mapping[str, Any]) -> str:
    """hash(horn geometry + transforms + cabinet CAD + port geometry + moving surface + topology)."""
    return domain_sha16("system.assembly_geometry_v1", payload)


def system_physics_id(payload: Mapping[str, Any]) -> str:
    """hash(assembly + solver/env + mesh + source + frequencies + observation)."""
    return domain_sha16("system.physics_v1", payload)


def system_analysis_id(payload: Mapping[str, Any]) -> str:
    """hash(analysis methods + samples applied to one physics response)."""
    return domain_sha16("system.analysis_v1", payload)


def system_score_id(payload: Mapping[str, Any]) -> str:
    """hash(analysis + system objective version + thresholds + weights)."""
    return domain_sha16("system.score_v1", payload)


def system_study_id(payload: Mapping[str, Any]) -> str:
    """hash(candidate pool + constraints + optimizer + seed)."""
    return domain_sha16("system.study_v1", payload)


def system_objective_id(payload: Mapping[str, Any]) -> str:
    return domain_sha16(f"system.objective_v{SYSTEM_OBJECTIVE_VERSION}", payload)
