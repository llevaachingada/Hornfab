"""BO metric policy for objective v11 (v10 coverage/ripple + required CD matrix block).

Pinned: the v4/v7 ``freeze_metric_policy`` still refuses v11 (and the v10 freezer refuses it);
the separate v11 policy is a distinct deterministic identity that carries the ``objective.cd``
block and the ``scalar_v11`` code sha; its raw observation reuses the v10 coverage/ripple
helpers; and a cohort never mixes v10/v11 labels.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.metrics import (
    METRIC_SCHEMA_V10,
    METRIC_SCHEMA_V11,
    assert_single_objective_cohort,
    freeze_metric_policy,
    freeze_metric_policy_for_version,
    freeze_metric_policy_v10,
    freeze_metric_policy_v11,
    measure_metrics_for_policy,
    measure_metrics_v11,
)
from hornlab_search.objective.replay import Brief
from hornlab_search.objective.scalar_v9 import _cov_profile_term
from hornlab_search.objective.scalar_v10 import V10Params, _rip_term_v10
from hornlab_search.objective.scalar_v11 import V11Params

from test_bo_metrics_adapter import fixture as _v4_fixture
from test_bo_metrics_v10 import F, ONES, _brief as _v10_brief, _metrics, _response, _target

CD_BLOCK = {
    "band_hz": [700.0, 8000.0],
    "window_h_deg": 30.0,
    "window_v_deg": 10.0,
    "lw": {"weight": 1.5, "tolerance_db": 1.5},
    "di_std": {"weight": 0.75, "tolerance_db": 1.0},
    "nacc": {"weight": 0.75, "tolerance": 0.02},
    "offaxis": {
        "weight": 1.0,
        "tolerance_db": 1.0,
        "reference": "band_mean",
        "band_hz": [2500.0, 8000.0],
        "angles_h_deg": [-40.0, -30.0, 30.0, 40.0],
        "angles_v_deg": [-25.0, -10.0, 10.0, 25.0],
    },
    "report": {"omega": True, "contour": False},
}


def _block():
    return {"version": 11, "tolerances": dict(ONES), "ripple_region": "preferred_edge",
            "cd": dict(CD_BLOCK)}


def _brief():
    block = _block()
    return Brief("v11fixture", _target(), {}, 11, block, V11Params.from_block(block))


def test_v4_v7_policy_still_refuses_v11():
    with pytest.raises(ValueError, match="v4 or v7"):
        freeze_metric_policy(_brief(), F)


def test_v10_policy_still_refuses_v11():
    with pytest.raises(ValueError, match="v10"):
        freeze_metric_policy_v10(_brief(), F)


def test_v11_policy_refuses_other_versions():
    _b4, _f4, _m4, _r4 = _v4_fixture()
    for brief in (_b4, _v10_brief(), _v10_brief(version=9)):
        with pytest.raises(ValueError, match="v11"):
            freeze_metric_policy_v11(brief, F)


def test_v11_policy_is_a_distinct_deterministic_identity_with_cd_block():
    a = freeze_metric_policy_v11(_brief(), F)
    b = freeze_metric_policy_v11(_brief(), F)
    assert a.physical_metric_spec_hash == b.physical_metric_spec_hash      # stable
    assert a.payload["schema"] == METRIC_SCHEMA_V11 and a.payload["objective_version"] == 11
    assert a.payload["cd"] == CD_BLOCK
    assert a.payload["ripple_region"] == {"mode": "preferred_edge"}
    code = a.payload["code_sha256"]
    assert "hornlab_search.objective.scalar_v11" in code
    assert "hornlab_search.metrics.cd" in code
    p10 = freeze_metric_policy_v10(_v10_brief(), F)
    b4, f4, _m4, _r4 = _v4_fixture()
    p4 = freeze_metric_policy(b4, f4)
    hashes = {a.physical_metric_spec_hash, p10.physical_metric_spec_hash,
              p4.physical_metric_spec_hash}
    assert len(hashes) == 3                                                # never the same identity


def test_v11_observation_matches_the_v10_raw_helpers():
    p = freeze_metric_policy_v11(_brief(), F)
    m, r = _metrics(), _response(bump_deg=37.5)
    o = measure_metrics_v11(p, m, r)
    assert o.status == "complete", o.reason
    assert o.physical_metric_spec_hash == p.physical_metric_spec_hash
    t = _target()
    band = (F >= 700.0) & (F <= 8000.0)
    params = V11Params.from_block(_brief().objective_block)
    assert o.coverage_deg == pytest.approx(
        _cov_profile_term(m, t, F, band, params.v10.v9), rel=1e-12)
    assert o.ripple_db == pytest.approx(
        _rip_term_v10(m, r, t, F, band, params.v10.ripple_region), rel=1e-12)


def test_v11_measure_refusals():
    p = freeze_metric_policy_v11(_brief(), F)
    assert measure_metrics_v11(p, _metrics(), None).status == "capability_missing"
    m = _metrics()
    m.bw_v_deg[2] = np.nan
    assert measure_metrics_v11(p, m, _response()).status == "capability_missing"
    tampered = type(p)(p.payload_json.replace("preferred_edge", "min_edge"),
                       p.physical_metric_spec_hash)
    assert measure_metrics_v11(tampered, _metrics(), _response()).reason == \
        "metric policy hash mismatch"
    import hashlib
    wrong_json = p.payload_json.replace(METRIC_SCHEMA_V11, METRIC_SCHEMA_V10)
    wrong = type(p)(wrong_json, hashlib.sha256(wrong_json.encode()).hexdigest())
    assert measure_metrics_v11(wrong, _metrics(), _response()).reason == \
        "not a v11 metric policy"


def test_explicit_dispatch_routes_by_resolved_version_without_fallback():
    p11 = freeze_metric_policy_for_version(_brief(), F)
    assert p11.payload["schema"] == METRIC_SCHEMA_V11
    assert measure_metrics_for_policy(p11, _metrics(), _response()).status == "complete"
    p10 = freeze_metric_policy_for_version(_v10_brief(), F)
    assert p10.payload["schema"] == METRIC_SCHEMA_V10
    assert measure_metrics_for_policy(p10, _metrics(), _response()).status == "complete"
    b4, f4, m4, r4 = _v4_fixture()
    p4 = freeze_metric_policy_for_version(b4, f4)
    assert p4.payload["objective_version"] == 4
    assert measure_metrics_for_policy(p4, m4, r4).status == "complete"
    with pytest.raises(ValueError, match="unsupported objective v9"):
        freeze_metric_policy_for_version(_v10_brief(version=9), F)
    mismatched = type(p11)(p11.payload_json.replace(METRIC_SCHEMA_V11, METRIC_SCHEMA_V10),
                           p11.physical_metric_spec_hash)
    with pytest.raises(ValueError, match="cannot be measured"):
        measure_metrics_for_policy(mismatched, _metrics(), _response())


def test_cohort_never_mixes_v10_v11_labels():
    p10 = freeze_metric_policy_v10(_v10_brief(), F)
    p11 = freeze_metric_policy_v11(_brief(), F)
    assert assert_single_objective_cohort([10, 10, p10]) == 10
    assert assert_single_objective_cohort([11, 11, p11]) == 11
    for mix in ([10, 11], [11, 10], [p10, 11], [p11, 10], [p10, p11]):
        with pytest.raises(ValueError, match="mixed objective labels"):
            assert_single_objective_cohort(mix)
    with pytest.raises(ValueError, match="unknown objective label"):
        assert_single_objective_cohort([12])
