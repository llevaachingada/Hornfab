"""Plan R8: dataset records carry optional config / brief / generator provenance. Offline."""
from __future__ import annotations

import json
from types import SimpleNamespace

from hornlab_search.dataset.record import build_record, validate_record
from hornlab_search.design.generated import brief_hash
from hornlab_search.search.evaluate import EvalContext, _record_provenance, record_provenance
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec


def _built(**kw):
    return build_record(make_eval(3), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                        area_m2=0.125, created_utc="2026-10-13T00:00:00Z", **kw)


def test_record_without_provenance_is_unchanged_and_valid():
    meta, _ = _built()
    assert "provenance" not in meta
    validate_record(meta)


def test_record_with_provenance_round_trips_and_validates():
    prov = {"config": "perturbed_osse_hv", "brief": "hifi_90x60_1in", "brief_hash": "31a78af10293",
            "generator": {"name": "typology", "knobs": {"L_mm": 120.0}}}
    meta, _ = _built(provenance=prov)
    validate_record(meta)
    assert json.loads(json.dumps(meta))["provenance"] == prov


def test_config_provenance_hashes_the_brief_like_the_generator_does():
    brief = {"name": "axi_90x90_1in", "target": {"coverage_h_deg": 90}}
    cfg = SimpleNamespace(raw={"name": "osse_axi", "brief": brief})
    assert record_provenance(cfg) == {"config": "osse_axi", "brief": "axi_90x90_1in",
                                      "brief_hash": brief_hash(brief)}
    assert record_provenance(SimpleNamespace(raw={"name": "x"}))["brief_hash"] is None


def test_generator_block_overrides_and_is_recorded():
    ctx = EvalContext(target=None, weights={}, lib_shas={},
                      provenance={"config": "c", "brief": None, "brief_hash": None})
    st = {"generator": {"name": "typology", "spec": {}, "knobs": {"a": 1.0}, "brief": "b",
                        "brief_hash": "abc", "derived": {"big": 1}}}
    p = _record_provenance(ctx, st)
    assert p["brief"] == "b" and p["brief_hash"] == "abc" and p["config"] == "c"
    assert "derived" not in p["generator"] and p["generator"]["knobs"] == {"a": 1.0}
