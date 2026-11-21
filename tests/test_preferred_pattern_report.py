"""Report-only tests use analytical cut samples and synthetic impedance."""
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.report.preferred_pattern import impedance_diagnostics, preferred_pattern_diagnostics


def response():
    angles = np.arange(-90., 91., 5.)
    # Exact threshold interpolations depend on the repository's -6 dB convention.
    h = np.tile(-6.020599913 * (angles / 40) ** 2, (4, 1))
    v = np.tile(-6.020599913 * (angles / 25) ** 2, (4, 1))
    return SimpleNamespace(freqs_hz=np.array([900., 1500., 3000., 8000.]),
                           h_angles_deg=angles, v_angles_deg=angles, spl_h_db=h, spl_v_db=v,
                           spl_balloon_db=None, balloon_dirs=None, meta={},
                           z_throat=np.array([.2+1j, .8+2j, 1.2-1j, .9+0j]))


def test_preferred_pattern_reports_widths_errors_and_sustained_onset():
    out = preferred_pattern_diagnostics(response())
    h, v = out['planes']['h'], out['planes']['v']
    np.testing.assert_allclose(h['width_deg'], 80, atol=.01)
    np.testing.assert_allclose(v['width_deg'], 50, atol=.01)
    assert abs(h['mean_signed_error_deg']) < .01
    assert v['rms_error_deg'] < .01
    assert h['corridor_onset']['status'] == 'censored_low'
    assert h['total_samples_in_band'] == 3
    assert out['balloon']['status'] == 'missing'


def test_censored_width_never_becomes_180_degree_measurement():
    r = response()
    r.spl_h_db[2] = 0
    h = preferred_pattern_diagnostics(r)['planes']['h']
    assert h['width_deg'][2] is None
    assert h['valid_samples_in_band'] == 2
    assert h['corridor_onset']['status'] == 'not_reached'


def test_impedance_extrema_and_missing():
    r = response()
    out = impedance_diagnostics(r, onset_threshold=.7)
    assert out['mean_resistance'] == pytest.approx(.775)
    assert out['resistance_extrema']['max'] == {'frequency_hz': 3000., 'value': 1.2}
    assert out['reactance_extrema']['local_troughs'] == [{'frequency_hz': 3000., 'value': -1.}]
    assert out['loading_onset']['onset_hz'] == 1500
    r.z_throat = None
    assert impedance_diagnostics(r)['status'] == 'missing'


def test_reject_invalid_band():
    with pytest.raises(ValueError):
        preferred_pattern_diagnostics(response(), band_hz=(8000, 900))
