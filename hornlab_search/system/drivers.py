"""System driver layer: reuse the frozen cone loader + a strict geometry schema v1.

Two sources of truth are reused, never re-implemented:

* **T/S parameters** come from :func:`hornlab_search.meh.drivers.load_cone`, i.e. the existing
  ``examples/drivers/<stem>.yaml`` C8 schema (``kind: cone``). No new driver YAML is created by
  this module and the schema is not extended.
* **Installation geometry** is a *new, additive* system schema (version 1) for
  ``examples/systems/driver_geometry/<driver_id>.yaml``. Its numeric keys map 1:1 onto
  :class:`hornlab_search.system.contracts.DriverGeometry`:

  ``cutout_mm, frame_od_mm, depth_mm, cone_depth_mm, surround_width_mm,
  dust_cap_diameter_mm, mounting_depth_behind_baffle_mm``

  plus three required provenance keys: ``driver_id``, ``sourced_from`` (a list of http(s) URLs)
  and ``measured_by`` (``"manufacturer"`` | ``"maker_cad"`` | ``"owner_measure"``).

Schema rules:

* unknown keys are hard errors (:class:`~hornlab_search.system.contracts.SchemaError`);
* every *declared* geometry value must be a finite number > 0 — an explicit ``null`` is a
  declaration error, not an "unknown" (omit the key instead);
* ``sourced_from`` must be a non-empty list of ``http(s)`` URLs;
* a driver with T/S data only is still usable for LF T/S screening, but cannot claim installed
  boundary fidelity (:func:`geometry_completeness`).

Units are the datasheet units already used by ``DriverGeometry``: millimetres.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from hornlab_search.meh.drivers import ConeDriver, load_cone
from hornlab_search.system.contracts import (
    DataQualityError,
    DriverGeometry,
    SchemaError,
    WooferDriver,
)

__all__ = [
    "GEOMETRY_DIR",
    "GEOMETRY_FIELDS",
    "INSTALLED_GEOMETRY_FIELDS",
    "MEASURED_BY_VALUES",
    "GEOMETRY_KEYS",
    "DriverGeometryDocument",
    "geometry_completeness",
    "missing_installed_fields",
    "require_fidelity",
    "parse_driver_geometry_dict",
    "load_driver_geometry",
    "load_woofer",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
GEOMETRY_DIR = REPO_ROOT / "examples" / "systems" / "driver_geometry"

#: The numeric keys of the system geometry schema (contracts.DriverGeometry fields).
GEOMETRY_FIELDS: tuple[str, ...] = (
    "cutout_mm",
    "frame_od_mm",
    "depth_mm",
    "cone_depth_mm",
    "surround_width_mm",
    "dust_cap_diameter_mm",
    "mounting_depth_behind_baffle_mm",
)

#: Every one of these describes the installed moving surface / baffle interface. All are
#: required before INSTALLED_EXTERIOR_BEM or COUPLED_VENTED_FEM_BEM_LEM may be claimed.
INSTALLED_GEOMETRY_FIELDS: tuple[str, ...] = GEOMETRY_FIELDS

MEASURED_BY_VALUES: tuple[str, ...] = ("manufacturer", "maker_cad", "owner_measure")
REQUIRED_META_KEYS: tuple[str, ...] = ("driver_id", "sourced_from", "measured_by")
GEOMETRY_KEYS: frozenset[str] = frozenset(REQUIRED_META_KEYS) | frozenset(GEOMETRY_FIELDS)


@dataclass(frozen=True)
class DriverGeometryDocument:
    """One parsed geometry YAML: the contract geometry plus its schema metadata."""

    driver_id: str
    geometry: DriverGeometry
    measured_by: str
    sourced_from: tuple[str, ...]

    @property
    def present_fields(self) -> tuple[str, ...]:
        return tuple(f for f in GEOMETRY_FIELDS if getattr(self.geometry, f) is not None)

    @property
    def completeness(self) -> Mapping[str, bool]:
        return geometry_completeness(self.present_fields)


# --------------------------------------------------------------------------- completeness

def _present(fields: Iterable[str] | Mapping[str, Any]) -> set[str]:
    """Normalise a field-name iterable or a mapping to the set of non-None geometry fields."""
    if isinstance(fields, Mapping):
        return {k for k, v in fields.items() if k in GEOMETRY_FIELDS and v is not None}
    return {str(f) for f in fields if str(f) in GEOMETRY_FIELDS}


def missing_installed_fields(fields: Iterable[str] | Mapping[str, Any]) -> tuple[str, ...]:
    """Which installed-surface fields are still unknown (empty tuple == complete)."""
    present = _present(fields)
    return tuple(f for f in INSTALLED_GEOMETRY_FIELDS if f not in present)


def geometry_completeness(fields: Iterable[str] | Mapping[str, Any]) -> Mapping[str, bool]:
    """Classify which :data:`~hornlab_search.system.contracts.Fidelity` tiers a driver supports.

    ``fields`` is the set of known geometry field names (or a mapping of field -> value).
    T/S screening needs no geometry and is always supported by this classifier; the two
    installed/fabrication fidelity tiers require the *full* installed-surface geometry; and
    ``MEASURED_VALIDATED`` is never granted by a datasheet at all.

    Returns a plain ``{fidelity_name: bool}`` mapping so callers (incl. ``WooferDriver``
    ``data_quality``) can record it directly. ``DataQualityError`` is raised by the fidelity
    gate itself (:meth:`contracts.WooferDriver.require_geometry`), not here — this function only
    classifies.
    """
    missing = missing_installed_fields(fields)
    full = not missing
    return {
        "SCREEN_MAGNITUDE": True,
        "SCREEN_COMPLEX_APPROX": True,
        "INSTALLED_EXTERIOR_BEM": full,
        "COUPLED_VENTED_FEM_BEM_LEM": full,
        "MEASURED_VALIDATED": False,
    }


# --------------------------------------------------------------------------- fidelity gate

def require_fidelity(driver: WooferDriver, fidelity: str) -> None:
    """Raise unless ``driver`` can honestly support the requested fidelity tier.

    T/S-only drivers pass ``"SCREEN_MAGNITUDE"`` / ``"SCREEN_COMPLEX_APPROX"``; an installed tier
    needs every :data:`INSTALLED_GEOMETRY_FIELDS` value. ``"MEASURED_VALIDATED"`` is never granted
    by this data layer.
    """
    known = set(geometry_completeness(()))
    if fidelity not in known:
        raise SchemaError(f"unknown fidelity {fidelity!r}; expected one of {sorted(known)}")
    geometry = driver.geometry_mm
    present = () if geometry is None else tuple(
        f for f in GEOMETRY_FIELDS if getattr(geometry, f) is not None)
    completeness = geometry_completeness(present)
    if not completeness[fidelity]:
        missing = missing_installed_fields(present)
        raise DataQualityError(
            f"driver {driver.driver_id!r} cannot claim {fidelity}: "
            f"missing installed geometry {list(missing) if missing else 'measurement data'}")


# --------------------------------------------------------------------------- parsing

def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"geometry.{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _positive_float(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"geometry.{name} must be a number, got {value!r}")
    x = float(value)
    if not math.isfinite(x) or x <= 0.0:
        raise SchemaError(f"geometry.{name} must be finite and > 0, got {value!r}")
    return x


def parse_driver_geometry_dict(d: Mapping[str, Any]) -> DriverGeometryDocument:
    """Parse one system geometry document (schema version 1). Unknown keys are hard errors."""
    if not isinstance(d, Mapping):
        raise SchemaError(f"geometry document must be a mapping, got {type(d).__name__}")

    unknown = set(d) - GEOMETRY_KEYS
    if unknown:
        raise SchemaError(f"unknown geometry keys: {sorted(unknown)}")

    missing_meta = [k for k in REQUIRED_META_KEYS if d.get(k) is None]
    if missing_meta:
        raise SchemaError(f"geometry document missing required key(s): {missing_meta}")

    driver_id = _require_text("driver_id", d["driver_id"])
    measured_by = _require_text("measured_by", d["measured_by"])
    if measured_by not in MEASURED_BY_VALUES:
        raise SchemaError(
            f"geometry.measured_by must be one of {MEASURED_BY_VALUES}, got {measured_by!r}")

    sourced = d["sourced_from"]
    if not isinstance(sourced, (list, tuple)) or not sourced:
        raise SchemaError("geometry.sourced_from must be a non-empty list of http(s) URLs")
    urls: list[str] = []
    for i, url in enumerate(sourced):
        text = _require_text(f"sourced_from[{i}]", url)
        if not text.startswith(("http://", "https://")):
            raise SchemaError(f"geometry.sourced_from[{i}] must be an http(s) URL, got {text!r}")
        urls.append(text)

    values: dict[str, float] = {}
    for name in GEOMETRY_FIELDS:
        if name not in d:
            continue
        value = d[name]
        if value is None:
            raise SchemaError(
                f"geometry.{name} is declared but null; omit the key if the value is unknown")
        values[name] = _positive_float(name, value)

    geometry = DriverGeometry(**values, source_urls=tuple(urls))
    return DriverGeometryDocument(
        driver_id=driver_id,
        geometry=geometry,
        measured_by=measured_by,
        sourced_from=tuple(urls),
    )


def load_driver_geometry(path: str | Path) -> DriverGeometryDocument:
    """Load one ``examples/systems/driver_geometry/*.yaml`` file (schema version 1)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return parse_driver_geometry_dict(data)


# --------------------------------------------------------------------------- woofer wrapper

def load_woofer(
    stem: str,
    *,
    geometry: str | Path | None = None,
    directory: str | Path | None = None,
) -> WooferDriver:
    """Load a real woofer: T/S from the frozen cone YAML, optional system geometry.

    ``stem`` / ``directory`` are passed straight to :func:`load_cone`, so the existing
    ``examples/drivers`` schema and provenance are reused unchanged. ``geometry`` is an optional
    path to a schema-v1 system geometry document; when absent the driver is T/S-only and every
    installed-fidelity claim is refused downstream.

    ``data_quality`` records the honest capability flags; it is not a score.
    """
    cone: ConeDriver = load_cone(stem, directory=directory)
    doc: DriverGeometryDocument | None = None
    if geometry is not None:
        doc = load_driver_geometry(geometry)
    geometry_mm = None if doc is None else doc.geometry
    present = () if doc is None else doc.present_fields
    completeness = geometry_completeness(present)
    data_quality = {
        "ts_source_present": bool(cone.source),
        "geometry_present": geometry_mm is not None,
        "has_full_geometry": bool(completeness["INSTALLED_EXTERIOR_BEM"]),
        "supports_lf_ts_screening": True,
        "supports_installed_exterior_bem": bool(completeness["INSTALLED_EXTERIOR_BEM"]),
        "supports_coupled_fidelity": bool(completeness["COUPLED_VENTED_FEM_BEM_LEM"]),
    }
    provenance: dict[str, Any] = {
        "driver_yaml": str(stem),
        "source_url": cone.source,
    }
    if doc is not None:
        provenance["geometry_driver_id"] = doc.driver_id
        provenance["measured_by"] = doc.measured_by
        provenance["sourced_from"] = list(doc.sourced_from)
    return WooferDriver(
        driver_id=str(stem),
        cone=cone,
        geometry_mm=geometry_mm,
        provenance=provenance,
        data_quality=data_quality,
    )
