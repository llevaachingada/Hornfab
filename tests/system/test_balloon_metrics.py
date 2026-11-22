"""Tests for the honest balloon power/DI helper (synthetic fixtures only, no BL)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import balloon_metrics as B  # noqa: E402

FREQS = np.array([100.0, 200.0])
DISTANCE_M = 2.0
CARDIOID_DI_DB = 4.771212547196624


# --------------------------------------------------------------------------- synthetic sphere


def _fibonacci_sphere(count: int = 4096) -> np.ndarray:
    """Deterministic equal-area unit vectors (the same construction BL uses)."""
    index = np.arange(count, dtype=np.float64) + 0.5
    z = 1.0 - 2.0 * index / count
    phi = index * np.pi * (3.0 - np.sqrt(5.0))
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.stack([radius * np.cos(phi), radius * np.sin(phi), z], axis=1)


def _observation(domain_id: str = "observation:sphere", *, kind: str = "spherical_observation",
                 directions: np.ndarray | None = None, distance_m: float | None = DISTANCE_M):
    dirs = _fibonacci_sphere() if directions is None else directions
    points = dirs * (DISTANCE_M if distance_m is None else distance_m)
    return SimpleNamespace(domain_id=domain_id, kind=kind, points_m=points,
                           distance_m=distance_m)


def _field(excitation_id: str, observation, p_pa, *, per_input: str = "normal_velocity_mps"):
    return SimpleNamespace(excitation_id=excitation_id, observation=observation,
                           p_pa=np.asarray(p_pa, dtype=np.complex128),
                           basis=SimpleNamespace(per_input=per_input))


def _result(fields, *, excitations=None, observations=None, frequencies=FREQS, **extra):
    fields = tuple(fields)
    if excitations is None:
        excitations = tuple(field.excitation_id for field in fields)
    if observations is None:
        observations = {}
        for field in fields:
            observations.setdefault(field.observation.domain_id, field.observation)
    return SimpleNamespace(
        frequencies_hz=np.asarray(frequencies, dtype=np.float64),
        excitation_ids=tuple(excitations),
        observation_sets=dict(observations),
        fields=fields,
        data_quality={},
        **extra,
    )


def _pressure(directions: np.ndarray, kind: str) -> np.ndarray:
    z = directions[:, 2]
    pattern = 0.5 * (1.0 + z) if kind == "cardioid" else z
    return np.tile(pattern.astype(np.complex128), (FREQS.size, 1))


# --------------------------------------------------------------------------- closed forms


def test_constant_pressure_is_zero_db() -> None:
    directions = _fibonacci_sphere()
    p_pa = np.full((FREQS.size, directions.shape[0]), complex(2.0, 1.0))
    axis = np.full(FREQS.size, complex(2.0, 1.0))

    np.testing.assert_allclose(B.power_response(p_pa), 5.0)
    np.testing.assert_allclose(B.di_db(axis, p_pa), 0.0, atol=1e-12)
    assert B.di_db(2.0 + 1.0j, p_pa[0]) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("kind", ["cardioid", "dipole"])
def test_cardioid_and_dipole_on_axis_read_4_771_db(kind: str) -> None:
    directions = _fibonacci_sphere()
    p_pa = _pressure(directions, kind)

    # Axis reference is exactly +Z (unit pressure for both synthetic patterns).
    di = B.di_db(np.ones(FREQS.size, dtype=np.complex128), p_pa)
    np.testing.assert_allclose(di, CARDIOID_DI_DB, rtol=0.0, atol=1e-3)

    # Equal-area mean(|p|^2) is 1/3 for both patterns; axis power is 1.
    np.testing.assert_allclose(B.power_response(p_pa), 1.0 / 3.0, atol=1e-4)


def test_equal_area_mean_and_weighted_mean() -> None:
    directions = _fibonacci_sphere()
    pattern = np.abs(_pressure(directions, "cardioid"))
    p_pa = pattern[:1]

    equal = B.power_response(p_pa)
    ones = B.power_response(p_pa, weights=np.ones(directions.shape[0]))
    np.testing.assert_allclose(equal, ones)

    # A one-hot weight set selects exactly one sample and normalises by the weight sum.
    one_hot = np.zeros(directions.shape[0])
    one_hot[7] = 1.0
    np.testing.assert_allclose(B.power_response(p_pa, weights=one_hot),
                               np.abs(p_pa[0, 7]) ** 2)


def test_non_finite_and_zero_axis_are_refused() -> None:
    p_pa = np.ones((2, 8), dtype=np.complex128)
    bad = p_pa.copy()
    bad[0, 0] = complex(np.nan, 0.0)
    with pytest.raises(ValueError, match="non-finite"):
        B.power_response(bad)
    with pytest.raises(ValueError, match="zero"):
        B.di_db(np.zeros(2, dtype=np.complex128), p_pa)
    with pytest.raises(ValueError, match="weights"):
        B.power_response(p_pa, weights=np.ones(9))


# --------------------------------------------------------------------------- per excitation


def test_per_excitation_separation_keeps_each_basis() -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    cardioid = _pressure(directions, "cardioid")
    voltage = _field("excitation:voltage", sphere, 2.0 * cardioid, per_input="V_rms")
    velocity = _field("excitation:velocity", sphere, 3.0 * cardioid,
                      per_input="normal_velocity_mps")
    result = _result([voltage, velocity],
                     excitations=("excitation:voltage", "excitation:velocity"))

    metrics = B.per_excitation_metrics(result)
    assert list(metrics) == ["excitation:voltage", "excitation:velocity"]

    # Scaling one excitation changes power but not DI; the two bases are never combined.
    np.testing.assert_allclose(metrics["excitation:voltage"]["power_pa2"],
                               4.0 / 3.0, atol=1e-3)
    np.testing.assert_allclose(metrics["excitation:velocity"]["power_pa2"],
                               9.0 / 3.0, atol=1e-3)
    np.testing.assert_allclose(metrics["excitation:voltage"]["di_db"],
                               metrics["excitation:velocity"]["di_db"], atol=1e-9)
    assert metrics["excitation:voltage"]["per_input"] == "V_rms"
    assert metrics["excitation:velocity"]["per_input"] == "normal_velocity_mps"
    for entry in metrics.values():
        assert entry["di_source"] == "balloon"
        assert entry["quadrature"] == "equal_area_fibonacci"
        assert entry["axis_source"] == "nearest_z_sample"
        assert len(entry["per_frequency"]) == FREQS.size
        assert set(entry["per_frequency"][0]) == {
            "freq_hz", "power_pa2", "di_db", "axis_source"}


def test_missing_probe_uses_nearest_z_sample_and_labels_it() -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    p_pa = _pressure(directions, "cardioid")
    result = _result([_field("excitation:velocity", sphere, p_pa)])

    metrics = B.per_excitation_metrics(result)
    entry = metrics["excitation:velocity"]
    nearest = int(np.argmax(directions[:, 2]))
    assert entry["axis_source"] == "nearest_z_sample"
    assert entry["axis_probe_id"] is None
    assert entry["axis_sample_index"] == nearest
    # DI is referenced to the actual nearest sample, not silently called on-axis.
    expected = B.di_db(p_pa[:, nearest], p_pa)
    np.testing.assert_allclose(entry["di_db"], expected)


def test_on_axis_probe_is_used_at_the_sphere_distance() -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    probe = _observation("observation:probe:on_axis_2m", kind="point_probe",
                         directions=np.array([[0.0, 0.0, 1.0]]))
    p_pa = _pressure(directions, "cardioid")
    axis_pa = np.ones((FREQS.size, 1), dtype=np.complex128)
    result = _result([
        _field("excitation:velocity", sphere, p_pa),
        _field("excitation:velocity", probe, axis_pa),
    ])

    metrics = B.per_excitation_metrics(result)
    entry = metrics["excitation:velocity"]
    assert entry["axis_source"] == "on_axis_probe"
    assert entry["axis_probe_id"] == "observation:probe:on_axis_2m"
    np.testing.assert_allclose(entry["di_db"], CARDIOID_DI_DB, atol=1e-3)
    assert entry["per_frequency"][0]["axis_source"] == "on_axis_probe"


def test_probe_at_a_different_distance_is_not_used_as_axis() -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    far_probe = _observation("observation:probe:on_axis_2m", kind="point_probe",
                             directions=np.array([[0.0, 0.0, 1.0]]), distance_m=4.0)
    p_pa = _pressure(directions, "cardioid")
    result = _result([
        _field("excitation:velocity", sphere, p_pa),
        _field("excitation:velocity", far_probe,
               np.ones((FREQS.size, 1), dtype=np.complex128)),
    ])
    entry = B.per_excitation_metrics(result)["excitation:velocity"]
    assert entry["axis_source"] == "nearest_z_sample"


@pytest.mark.parametrize("marker", ["combined", "sum", "total"])
def test_combined_multi_excitation_sum_is_refused(marker: str) -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    p_pa = _pressure(directions, "cardioid")
    name = f"excitation:{marker}"
    result = _result([_field(name, sphere, p_pa)], excitations=(name,))
    with pytest.raises(ValueError, match=B.COMBINED_EXCITATION_REFUSED):
        B.per_excitation_metrics(result)


def test_combined_p_total_is_refused() -> None:
    directions = _fibonacci_sphere()
    sphere = _observation()
    p_pa = _pressure(directions, "cardioid")
    result = _result([_field("excitation:velocity", sphere, p_pa)],
                     p_total=np.zeros_like(p_pa))
    with pytest.raises(ValueError, match=B.COMBINED_EXCITATION_REFUSED):
        B.per_excitation_metrics(result)


def test_missing_sphere_is_refused_with_a_token() -> None:
    probe = _observation("observation:probe:on_axis_2m", kind="point_probe",
                         directions=np.array([[0.0, 0.0, 1.0]]))
    result = _result([_field("excitation:velocity", probe,
                             np.ones((FREQS.size, 1), dtype=np.complex128))])
    with pytest.raises(ValueError, match=B.NO_SPHERICAL_DOMAIN):
        B.per_excitation_metrics(result)
