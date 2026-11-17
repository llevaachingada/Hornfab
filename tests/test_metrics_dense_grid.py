"""Stage 1 WP 1.2 (2026-11-17): dense log-frequency score grid for objective v9."""
import math

import numpy as np
import pytest

from hornlab_search.metrics import dense_grid as D
from hornlab_search.types import Response


def _resp(nf=18, with_p=True):
    f = np.geomspace(350.0, 8000.0, nf)
    ang = np.arange(-90.0, 91.0, 5.0)
    bw = 120.0 - 25.0 * np.log10(f / 350.0)                      # narrowing beam (deg)
    sig = (bw[:, None] / 2.0) / math.sqrt(2 * math.log(2.0)) * math.sqrt(2.0)
    spl = 90.0 + 3.0 * np.log10(f)[:, None] - 6.0 * (ang[None, :] / (bw[:, None] / 2.0)) ** 2 / 1.0
    z = (0.3 + 0.6 * (1 - np.exp(-f / 1000.0))) + 0.1j
    p = (10 ** (spl / 20.0)).astype(complex) if with_p else None
    return Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang, spl_h_db=spl,
                    spl_v_db=spl - 0.5, balloon_dirs=None, spl_balloon_db=None, z_throat=z,
                    p_h=p, p_v=p, meta={})


def test_dense_response_grid_and_exactness_on_log_linear_data():
    r = _resp()
    d = D.dense_response(r, 116, 350.0, 8000.0)
    assert d.freqs_hz.size == 116 and d.freqs_hz[0] == pytest.approx(350.0)
    assert d.freqs_hz[-1] == pytest.approx(8000.0)
    # on-axis SPL is linear in log f -> PCHIP reproduces it exactly
    ax = int(np.argmin(np.abs(r.h_angles_deg)))
    assert np.allclose(d.spl_h_db[:, ax], 90.0 + 3.0 * np.log10(d.freqs_hz), atol=1e-9)
    assert d.p_h is None and d.p_v is None and d.meta["score_grid"]["points"] == 116
    assert r.p_h is not None                       # the input is never mutated


def test_dense_response_never_extrapolates():
    d = D.dense_response(_resp(), 58, 200.0, 20000.0)
    assert d.freqs_hz[0] == pytest.approx(350.0) and d.freqs_hz[-1] == pytest.approx(8000.0)


@pytest.mark.parametrize("raw,match", [
    ({"kind": "dense_lin", "points": 58}, "kind"),
    ({"kind": "dense_log", "points": 57}, "points"),
    ({"kind": "dense_log", "points": True}, "points"),
    ({"kind": "dense_log", "points": 58, "x": 1}, "unknown"),
])
def test_score_grid_block_validation(raw, match):
    with pytest.raises(ValueError, match=match):
        D.validate_score_grid(raw)


def test_v9_score_grid_is_opt_in_and_needs_a_response():
    from hornlab_search.objective.scalar_v9 import V9Params, V9_WEIGHTED_KEYS, objective_v9
    tol = {k: 1.0 for k in V9_WEIGHTED_KEYS}
    p0 = V9Params.from_block({"version": 9, "tolerances": tol})
    p = V9Params.from_block({"version": 9, "tolerances": tol,
                             "score_grid": {"kind": "dense_log", "points": 58}})
    assert "score_grid" not in p0.to_block() and p.to_block()["score_grid"]["points"] == 58
    from hornlab_search.targets.spec import Target
    t = Target.from_dict({"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
                          "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0,
                          "z_min": 0.0, "coverage_profile": {
                              "mode": "corridor", "interpolation": "log_frequency",
                              "h": [{"hz": 700.0, "preferred_deg": 75.0, "min_deg": 60.0, "max_deg": 90.0},
                                    {"hz": 8000.0, "preferred_deg": 75.0, "min_deg": 60.0, "max_deg": 90.0}],
                              "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
                                    {"hz": 8000.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0}]}})
    from hornlab_search.search.evaluate import metrics_from_response
    r = _resp()
    m = metrics_from_response(r, t)
    j0, t0 = objective_v9(m, r, True, t, None, p0)
    j1, t1 = objective_v9(m, r, True, t, None, p)
    assert math.isfinite(j0) and math.isfinite(j1) and t0["penalty"] == 0.0 and t1["penalty"] == 0.0
    assert t1["n_in_band"] > t0["n_in_band"]               # scored on the dense grid
    jn, tn = objective_v9(m, None, True, t, None, p)       # no response -> failure penalty
    assert tn["penalty"] > 0.0
