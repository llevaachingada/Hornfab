"""Report-only directivity extras (CEA-2034 subset + forward beam shape) wired into
metrics_from_response: present, finite on a real-shaped response, never in J, never raising."""
import dataclasses
import math

import numpy as np

from conftest import make_fake_response
from hornlab_search.objective import objective
from hornlab_search.search.evaluate import EXTRA_SCALAR_KEYS, directivity_extras, metrics_from_response
from hornlab_search.targets.spec import Target

TARGET = Target.from_dict({"coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
                           "band_lo_hz": 500.0, "band_hi_hz": 20000.0})
W = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0}


def test_extras_present_and_do_not_change_the_objective():
    resp = make_fake_response()
    m = metrics_from_response(resp, TARGET)
    assert set(EXTRA_SCALAR_KEYS) <= set(m.scalars)
    if m.di_source == "balloon":
        assert math.isfinite(m.scalars["spdi_mean_db"])
    assert math.isfinite(m.scalars["lw_minus_on_axis_mean_db"])
    stripped = dataclasses.replace(m, scalars={k: v for k, v in m.scalars.items()
                                               if k not in EXTRA_SCALAR_KEYS})
    assert objective(m, True, TARGET, W) == objective(stripped, True, TARGET, W)


def test_extras_never_raise_on_broken_input():
    resp = make_fake_response()
    m = metrics_from_response(resp, TARGET)
    broken = dataclasses.replace(resp, spl_v_db=np.full_like(resp.spl_v_db, np.nan),
                                 balloon_dirs=np.zeros((3, 3)), spl_balloon_db=np.zeros((len(resp.freqs_hz), 3)))
    out = directivity_extras(broken, m, TARGET)
    assert set(out) == set(EXTRA_SCALAR_KEYS)            # all keys, NaN where not computable
