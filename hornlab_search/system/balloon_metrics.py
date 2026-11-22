"""Honest balloon power / directivity metrics from Boundary Lab headless results.

Boundary Lab's full-sphere observation (``spherical_sampling_enabled`` project
preference) is an **equal-area Fibonacci point set**; the per-input normalisation is
declared per excitation by :mod:`hornlab_search.system.boundarylab.bl_results`
(``Pa`` RMS for either a ``1 m/s`` normal-velocity port or a ``2.83 V`` voltage port).
Equal weights are therefore correct for the sphere mean -- no ``sin(theta)`` factor is
applied.  The quadrature is recorded as ``equal_area_fibonacci`` so a DI read from these
numbers can never be mistaken for a theta-phi-grid average.

Everything here is **per excitation**.  A voltage-referenced and a velocity-referenced
pressure field are different sensitivity bases; combining them into one "DI" would mix
references and is refused (:data:`COMBINED_EXCITATION_REFUSED`).

The axis reference is, in order of preference:

* the same-excitation on-axis probe at the sphere's distance
  (``axis_source="on_axis_probe"``);
* otherwise the sphere sample nearest +Z (``axis_source="nearest_z_sample"``).  This
  fallback is labelled, never silently called "on-axis".
"""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

__all__ = [
    "AXIS_SOURCE_NEAREST_Z_SAMPLE",
    "AXIS_SOURCE_ON_AXIS_PROBE",
    "COMBINED_EXCITATION_REFUSED",
    "DI_SOURCE",
    "NO_SPHERICAL_DOMAIN",
    "QUADRATURE",
    "di_db",
    "per_excitation_metrics",
    "power_response",
]

DI_SOURCE = "balloon"
QUADRATURE = "equal_area_fibonacci"
AXIS_SOURCE_ON_AXIS_PROBE = "on_axis_probe"
AXIS_SOURCE_NEAREST_Z_SAMPLE = "nearest_z_sample"
NO_SPHERICAL_DOMAIN = "NO_SPHERICAL_DOMAIN"
COMBINED_EXCITATION_REFUSED = "COMBINED_EXCITATION_REFUSED"

#: Relative tolerance used when asking whether a probe sits at the balloon radius.
_DISTANCE_RTOL = 1e-6
#: How far a "on-axis" probe may sit off the +Z axis (in unit-direction components).
_ON_AXIS_ABS_TOL = 1e-3


def _as_complex(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.complex128)
    if array.size == 0:
        raise ValueError(f"{name} is empty; a pressure field is required")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values; refusing a false DI")
    return array


def _as_weights(weights: Any, count: int) -> np.ndarray | None:
    if weights is None:
        return None
    array = np.asarray(weights, dtype=np.float64)
    if array.ndim != 1 or array.size != count:
        raise ValueError(
            f"weights must be a 1-D array of {count} values, got shape {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError("weights contain non-finite values")
    if np.any(array < 0.0):
        raise ValueError("weights must be non-negative")
    if float(np.sum(array)) <= 0.0:
        raise ValueError("weights sum to zero; an equal-area or weighted mean is undefined")
    return array


def power_response(p_pa: Any, weights: Any = None) -> np.ndarray:
    """Mean ``|p|^2`` over the observation sphere (Pa^2).

    ``p_pa`` has observations on its last axis (``(nf, nobs)`` in the BL reader).
    ``weights=None`` is the equal-area mean, which is exact for BL's Fibonacci sphere.
    A weighted mean is available for non-equal-area grids and is normalised by the
    weight sum.
    """
    p = _as_complex(p_pa, "p_pa")
    if p.ndim == 0:
        raise ValueError("p_pa must have at least one observation axis")
    power = np.abs(p) ** 2
    w = _as_weights(weights, int(p.shape[-1]))
    if w is None:
        return np.mean(power, axis=-1)
    return np.sum(power * w, axis=-1) / float(np.sum(w))


def di_db(axis_pa: Any, p_pa: Any, weights: Any = None) -> float | np.ndarray:
    """``10 * log10(|axis|^2 / mean(|p|^2))`` in dB.

    Both inputs are complex pressure arrays in the same per-input basis.  The axis may be
    a scalar, a per-frequency vector, or broadcast against the balloon array.  Zero or
    non-finite powers have no defined DI and raise instead of returning a made-up value.
    """
    axis = _as_complex(axis_pa, "axis_pa")
    mean_power = np.asarray(power_response(p_pa, weights), dtype=np.float64)
    axis_power = np.abs(axis) ** 2
    if np.any(axis_power <= 0.0):
        raise ValueError("axis pressure is zero; directivity index is undefined")
    if np.any(mean_power <= 0.0):
        raise ValueError("balloon mean power is zero; directivity index is undefined")
    try:
        ratio = axis_power / mean_power
    except ValueError as exc:  # pragma: no cover - numpy's message is clear already
        raise ValueError(f"axis and balloon shapes are not compatible: {exc}") from None
    result = 10.0 * np.log10(ratio)
    if not np.all(np.isfinite(result)):
        raise ValueError("directivity index is non-finite; refusing a false DI")
    return float(result) if np.ndim(result) == 0 else result


# --------------------------------------------------------------------------- result views


def _is_spherical(observation: Any) -> bool:
    kind = str(getattr(observation, "kind", "")).lower()
    return kind in ("spherical_observation", "bl_spherical_observation") or "spherical" in kind


def _select_sphere(result: Any, sphere_domain_id: str | None) -> Any:
    sets = dict(getattr(result, "observation_sets", {}) or {})
    if sphere_domain_id is not None:
        observation = sets.get(sphere_domain_id)
        if observation is None:
            raise ValueError(
                f"{NO_SPHERICAL_DOMAIN}: domain {sphere_domain_id!r} is not in the result; "
                f"available: {sorted(sets)}")
        if not _is_spherical(observation):
            raise ValueError(
                f"{NO_SPHERICAL_DOMAIN}: domain {sphere_domain_id!r} kind is "
                f"{getattr(observation, 'kind', None)!r}, not a sphere")
        return observation
    spheres = [observation for observation in sets.values() if _is_spherical(observation)]
    if not spheres:
        raise ValueError(
            f"{NO_SPHERICAL_DOMAIN}: the result carries no spherical observation domain "
            f"(available kinds: {sorted({str(getattr(o, 'kind', '?')) for o in sets.values()})}); "
            "enable spherical_sampling_enabled in the project preferences")
    domain_ids = {observation.domain_id for observation in spheres}
    if len(domain_ids) > 1:
        raise ValueError(
            f"{NO_SPHERICAL_DOMAIN}: multiple spherical domains {sorted(domain_ids)}; pass "
            "sphere_domain_id to choose one explicitly")
    return spheres[0]


def _refuse_combined(result: Any) -> None:
    """Refuse a pre-summed / combined multi-excitation result (mixed references)."""
    if getattr(result, "p_total", None) is not None:
        raise ValueError(
            f"{COMBINED_EXCITATION_REFUSED}: a combined p_total mixes excitations (and often "
            "sensitivity references); balloon DI is computed per excitation only")
    quality = getattr(result, "data_quality", {}) or {}
    if isinstance(quality, Mapping) and (
            quality.get("combined_excitation") or quality.get("p_total_combined")
            or quality.get("excitation_sum")):
        raise ValueError(
            f"{COMBINED_EXCITATION_REFUSED}: the result declares a combined excitation sum; "
            "compute per excitation and keep each excitation's declared per-input basis")
    for name in tuple(getattr(result, "excitation_ids", ()) or ()):
        low = str(name).strip().lower()
        tail = low.rsplit(":", 1)[-1]
        tokens = set(tail.replace("-", "_").split("_"))
        if ("combined" in low or tail in {"sum", "total"}
                or tokens & {"sum", "total", "combined"}):
            raise ValueError(
                f"{COMBINED_EXCITATION_REFUSED}: excitation {name!r} looks like a combined "
                "sum; balloon DI is computed per independent excitation only")


def _field_index(field: Any) -> np.ndarray:
    values = np.asarray(getattr(field, "p_pa"), dtype=np.complex128)
    if values.ndim != 2:
        raise ValueError(
            f"balloon pressure for excitation {getattr(field, 'excitation_id', '?')!r} "
            f"must be (nf, nobs), got {values.shape}")
    return values


def _unit_directions(observation: Any) -> np.ndarray:
    points = np.asarray(getattr(observation, "points_m"), dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
        raise ValueError(
            f"sphere domain {getattr(observation, 'domain_id', '?')!r} points_m must be "
            f"(n, 3), got {points.shape}")
    if not np.all(np.isfinite(points)):
        raise ValueError("sphere points_m contains non-finite values")
    norms = np.linalg.norm(points, axis=1)
    if np.any(norms <= 0.0):
        raise ValueError("sphere points_m contains a zero-radius sample; cannot define an axis")
    return points / norms[:, None]


def _nearest_z_index(directions: np.ndarray) -> int:
    return int(np.argmax(directions[:, 2]))


def _same_distance(a: Any, b: Any) -> bool:
    left = getattr(a, "distance_m", None)
    right = getattr(b, "distance_m", None)
    if left is None or right is None:
        return False
    scale = max(abs(float(left)), abs(float(right)), 1e-12)
    return abs(float(left) - float(right)) <= max(1e-9, _DISTANCE_RTOL * scale)


def _probe_axis(result: Any, excitation_id: str, sphere: Any,
                axis_probe_id: str) -> tuple[np.ndarray | None, int | None]:
    sets = dict(getattr(result, "observation_sets", {}) or {})
    probe = sets.get(axis_probe_id)
    if probe is None or not _same_distance(probe, sphere):
        return None, None
    fields = tuple(getattr(result, "fields", ()) or ())
    field = next((candidate for candidate in fields
                  if getattr(candidate, "excitation_id", None) == excitation_id
                  and getattr(getattr(candidate, "observation", None), "domain_id", None)
                  == axis_probe_id), None)
    if field is None:
        return None, None
    directions = _unit_directions(probe)
    index = _nearest_z_index(directions)
    if (abs(float(directions[index, 0])) > _ON_AXIS_ABS_TOL
            or abs(float(directions[index, 1])) > _ON_AXIS_ABS_TOL
            or float(directions[index, 2]) <= 0.0):
        # A probe that is not actually on +Z must not be reported as an axis reference.
        return None, None
    return _field_index(field)[:, index], index


def per_excitation_metrics(
    result: Any,
    *,
    axis_probe_id: str = "observation:probe:on_axis_2m",
    sphere_domain_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute balloon power and DI for each single excitation in ``result``.

    ``result`` is a :class:`~hornlab_search.system.boundarylab.bl_results.BLHeadlessResult`
    (or an object with the same read-only attributes).  The return value is ordered like
    ``result.excitation_ids`` and each entry carries:

    ``frequencies_hz``, ``power_pa2``, ``di_db`` (arrays), ``axis_source``
    (``"on_axis_probe"`` or ``"nearest_z_sample"``), ``axis_probe_id``,
    ``axis_sample_index``, ``per_input``, ``domain_id``, ``distance_m``,
    ``di_source="balloon"``, ``quadrature="equal_area_fibonacci"`` and
    ``per_frequency`` (a list of ``{freq_hz, power_pa2, di_db, axis_source}``).

    Refusals: no sphere, multiple spheres without ``sphere_domain_id``, a combined /
    pre-summed excitation, non-finite fields, and a zero axis or sphere power.
    """
    _refuse_combined(result)
    sphere = _select_sphere(result, sphere_domain_id)
    directions = _unit_directions(sphere)
    nearest_index = _nearest_z_index(directions)

    fields = tuple(getattr(result, "fields", ()) or ())
    fields_by_excitation: dict[str, Any] = {}
    for field in fields:
        observation = getattr(field, "observation", None)
        if getattr(observation, "domain_id", None) != getattr(sphere, "domain_id", None):
            continue
        excitation_id = str(getattr(field, "excitation_id", ""))
        if not excitation_id:
            raise ValueError("balloon field has no excitation id")
        fields_by_excitation[excitation_id] = field

    raw_ids = getattr(result, "excitation_ids", ()) or ()
    excitation_ids: tuple[str, ...] = tuple(str(name) for name in raw_ids)
    if not excitation_ids:
        raise ValueError("result declares no excitation ids")
    missing = [name for name in excitation_ids if name not in fields_by_excitation]
    if missing:
        raise ValueError(
            f"BALLOON_EXCITATION_MISSING: no spherical pressure field for excitation(s) "
            f"{missing}; a partial balloon set cannot produce an honest DI")

    frequencies = np.asarray(getattr(result, "frequencies_hz"), dtype=np.float64)
    metrics: dict[str, dict[str, Any]] = {}
    for excitation_id in excitation_ids:
        field = fields_by_excitation[excitation_id]
        p_pa = _field_index(field)
        if p_pa.shape[0] != frequencies.size:
            raise ValueError(
                f"excitation {excitation_id!r} has {p_pa.shape[0]} frequencies but the result "
                f"declares {frequencies.size}")

        probe_pressure, probe_index = _probe_axis(result, excitation_id, sphere, axis_probe_id)
        if probe_pressure is not None:
            axis_pressure = probe_pressure
            axis_source = AXIS_SOURCE_ON_AXIS_PROBE
            axis_index: int | None = probe_index
            used_probe: str | None = axis_probe_id
        else:
            axis_pressure = p_pa[:, nearest_index]
            axis_source = AXIS_SOURCE_NEAREST_Z_SAMPLE
            axis_index = nearest_index
            used_probe = None

        power = np.asarray(power_response(p_pa), dtype=np.float64)
        directivity = np.asarray(di_db(axis_pressure, p_pa), dtype=np.float64)
        if power.shape != frequencies.shape or directivity.shape != frequencies.shape:
            raise ValueError(
                f"excitation {excitation_id!r} produced shapes {power.shape}/{directivity.shape} "
                f"for {frequencies.shape[0]} frequencies")

        per_frequency = [
            {
                "freq_hz": float(frequencies[index]),
                "power_pa2": float(power[index]),
                "di_db": float(directivity[index]),
                "axis_source": axis_source,
            }
            for index in range(frequencies.size)
        ]
        basis = getattr(field, "basis", None)
        metrics[excitation_id] = {
            "excitation_id": excitation_id,
            "domain_id": str(getattr(sphere, "domain_id", "")),
            "distance_m": getattr(sphere, "distance_m", None),
            "per_input": getattr(basis, "per_input", None),
            "frequencies_hz": frequencies.copy(),
            "power_pa2": power,
            "di_db": directivity,
            "axis_source": axis_source,
            "axis_probe_id": used_probe,
            "axis_sample_index": axis_index,
            "di_source": DI_SOURCE,
            "quadrature": QUADRATURE,
            "per_frequency": per_frequency,
        }
    return metrics
