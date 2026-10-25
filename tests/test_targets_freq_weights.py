"""WP4: ``Target.freq_weights`` validation and the v2 weight vector.

Absent / null ``freq_weights`` must keep the old behaviour (it is optional and no existing YAML
sets it). A PROVIDED value is now validated instead of being silently accepted and ignored.
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.objective.scalar_v2 import freq_weight_vector
from hornlab_search.targets.spec import Target, validate_freq_weights

BASE = {
    "coverage_h_deg": 90.0,
    "coverage_v_deg": 60.0,
    "band_lo_hz": 700.0,
    "band_hi_hz": 5500.0,
    "di_target_db": None,
}


def test_absent_or_null_freq_weights_is_still_optional():
    t = Target.from_dict(dict(BASE))
    assert t.freq_weights is None
    assert Target.from_dict({**BASE, "freq_weights": None}).freq_weights is None


def test_valid_freq_weights_round_trip_to_floats():
    t = Target.from_dict({**BASE, "freq_weights": {"band_hz": [["700", 2000, 0.5]]}})
    assert t.freq_weights == {"band_hz": [[700.0, 2000.0, 0.5]]}


def test_validator_returns_a_normalised_copy():
    src = {"band_hz": [[700, 2000, 2]]}
    out = validate_freq_weights(src)
    assert out == {"band_hz": [[700.0, 2000.0, 2.0]]}
    assert out is not src


@pytest.mark.parametrize("bad", [
    [],
    "band_hz",
    {"band_hz": 1},
    {"band_hz": [[700.0, 2000.0]]},
    {"band_hz": [[700.0, 2000.0, 0.5, 1.0]]},
    {"band_hz": [[0.0, 2000.0, 0.5]]},
    {"band_hz": [[2000.0, 700.0, 0.5]]},
    {"band_hz": [[700.0, 700.0, 0.5]]},
    {"band_hz": [[700.0, 2000.0, 0.0]]},
    {"band_hz": [[700.0, 2000.0, -1.0]]},
    {"band_hz": [[700.0, np.inf, 0.5]]},
    {"band_hz": [[700.0, 2000.0, np.nan]]},
    {"band_hz": [["x", 2000.0, 0.5]]},
    {"bands_hz": [[700.0, 2000.0, 0.5]]},
    {"band_hz": [[700.0, 2000.0, 0.5]], "extra": 1},
])
def test_malformed_freq_weights_raise_value_error(bad):
    with pytest.raises(ValueError):
        Target.from_dict({**BASE, "freq_weights": bad})


def test_unknown_top_level_key_still_raises_without_changing_behaviour():
    with pytest.raises(ValueError):
        Target.from_dict({**BASE, "target_wieghts": {}})


def test_freq_weight_vector_multiplies_matching_intervals():
    t = Target.from_dict({**BASE, "freq_weights": {
        "band_hz": [[700.0, 2000.0, 2.0], [2000.0, 5500.0, 0.5]]}})
    f = np.array([600.0, 700.0, 2000.0, 3000.0, 5500.0, 6000.0])
    assert freq_weight_vector(f, t).tolist() == [1.0, 2.0, 1.0, 0.5, 0.5, 1.0]


def test_freq_weight_vector_is_all_ones_without_weights():
    t = Target.from_dict(dict(BASE))
    assert np.array_equal(freq_weight_vector(np.array([500.0, 1000.0]), t), np.ones(2))


def test_hand_built_target_with_malformed_weights_raises_in_the_helper():
    t = Target(coverage_h_deg=90.0, coverage_v_deg=60.0, band_lo_hz=700.0,
               band_hi_hz=5500.0, di_target_db=None, freq_weights={"nope": 1})
    with pytest.raises(ValueError):
        freq_weight_vector(np.array([1000.0]), t)
