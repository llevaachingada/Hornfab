import json
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("botorch")

from hornlab_search.bo import diagnostics as D  # noqa: E402
from hornlab_search.bo.model import fit_model  # noqa: E402


def _ts(n, d=2, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.random((n, d))
    J = ((X - 0.4) ** 2).sum(1, keepdims=True) + 0.05 * np.sin(5 * X[:, :1]) + 0.1
    return SimpleNamespace(status="ok", d=d, n=n, X=X, J=J, Y=-J, n_min=8,
                           ids=tuple(f"r{i}" for i in range(n)),
                           active_keys=tuple(f"k{i}" for i in range(d)))


def _check_block(b, d):
    assert set(b["slices"]["per_key"]) == {f"k{i}" for i in range(d)}
    for s in b["slices"]["per_key"].values():
        assert len(s["x"]) == len(s["j_mean"]) == len(s["j_sd"]) == D.GRID_N
    assert b["loo"]["method"] == D.LOO_METHOD and len(b["loo"]["rows"]) == b["loo"]["n"]
    assert [r["rank"] for r in sorted(b["relevance"], key=lambda r: r["rank"])] == [1, 2][:d]


def test_scalar_artifact():
    ts = _ts(12)
    fit = fit_model(ts, seed=0)
    assert fit.ok, fit.detail
    out = D.build_diagnostics(fit, ts, "scalar", study_id="s", revision=1)
    assert out["schema"] == D.SCHEMA and out["status"] == "ok" and out["pareto"] is None
    _check_block(out, 2)
    assert out["slices"]["anchor_id"] == "r%d" % int(np.argmin(ts.J))
    assert out["size_bytes"] < D.MAX_BYTES
    json.dumps(out, allow_nan=False)


def test_unavailable_fit():
    ts = _ts(3)
    out = D.build_diagnostics(fit_model(ts, seed=0), ts, "scalar")
    assert out["status"] == "unavailable"


def test_pareto_artifact():
    from hornlab_search.bo.pareto import (ParetoTraining, fit_pareto_training,
                                          frozen_reference)
    n = 20
    ts = _ts(n, seed=1)
    rng = np.random.default_rng(2)
    errors = np.column_stack([ts.X[:, 0] * 10 + rng.random(n), (1 - ts.X[:, 0]) * 3 + rng.random(n)])
    pt = ParetoTraining(X=ts.X, errors=errors, J=ts.J.reshape(-1), ids=ts.ids,
                        geometry_ids=tuple(f"g{i}" for i in range(n)),
                        reference=frozen_reference(errors), metric_spec_hash="a" * 64)
    pf = fit_pareto_training(pt, seed=0)
    assert pf.status == "ok", pf.reason
    fit = fit_model(ts, seed=0)
    out = D.build_diagnostics(fit, ts, "pareto", {"fit": pf, "training": pt})
    assert out["status"] == "ok"
    assert set(out["per_objective"]) == {"coverage", "ripple"}
    for b in out["per_objective"].values():
        _check_block(b, 2)
    p = out["pareto"]
    assert p["front_ids"] and set(p["front_ids"]) <= set(ts.ids)
    hv = [t["hv"] for t in p["hv_trace"]]
    assert all(b >= a - 1e-9 for a, b in zip(hv, hv[1:])) and hv[-1] > 0


def test_loo_truncation_flag(monkeypatch):
    monkeypatch.setattr(D, "LOO_ROW_CAP", 5)
    ts = _ts(12)
    out = D.build_diagnostics(fit_model(ts, seed=0), ts, "scalar")
    assert out["loo"]["truncated"] and len(out["loo"]["rows"]) == 5 and out["loo"]["n"] == 12
