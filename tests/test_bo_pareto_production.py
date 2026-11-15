"""Production wiring for the Pareto policy (spec 3.5): bindings, frozen reference, evaluator.

Offline: a tiny synthetic dataset (stored metric + cut arrays) under a temp study root; no
solver, no mesh.  GP fitting needs the optional BoTorch engine and is skipped without it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.bo.pareto import ParetoTraining, frozen_reference
from hornlab_search.bo.policy import capability_status
from hornlab_search.studies import builders
from hornlab_search.studies.schema import Unavailable

from test_study_builders import ROWS, _pool, _service_with_study, _tiny_fixture

FREQS = np.geomspace(400.0, 7000.0, 12)
ANGLES = np.arange(-90.0, 91.0, 5.0)


def _arrays(i):
    cut = np.tile(-0.004 * (1 + 0.02 * i) * ANGLES ** 2, (FREQS.size, 1))
    cut = cut + 0.3 * np.sin(np.arange(FREQS.size) * (1 + i % 3))[:, None]
    return {
        "freqs_hz": FREQS, "bw_h_deg": np.full(FREQS.size, 60.0 + i),
        "bw_v_deg": np.full(FREQS.size, 50.0 - 0.5 * i), "di_db": np.full(FREQS.size, 8.0),
        "ripple_h_db": np.ones(FREQS.size), "ripple_v_db": np.ones(FREQS.size),
        "on_axis_db": np.zeros(FREQS.size), "h_angles_deg": ANGLES, "v_angles_deg": ANGLES,
        "spl_h_db": cut, "spl_v_db": cut,
    }


def _study(tmp_path, *, drop=()):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    dataset = Path(spec["source"]["dataset_root"])
    (dataset / "shard-0000").mkdir(exist_ok=True)
    for i in range(ROWS):
        if i in drop:
            continue
        np.savez(dataset / "shard-0000" / f"rec-{i:04d}.npz", **_arrays(i))
    for fn in (builders.freeze_snapshot, builders.build_training, builders.build_analysis):
        fn(service, sid, root=root, spec=spec)
    return service, sid, root, spec


def _payload(service, meta):
    return json.loads(service.store.read_artifact(meta["sha256"]))


def test_metric_observations_attached_reference_frozen_and_missing_rows_excluded(tmp_path):
    service, sid, root, _ = _study(tmp_path, drop=(3,))
    result = builders.build_pareto_metrics(service, sid, root=root)
    payload = _payload(service, result["artifact"])
    assert payload["n_complete"] == ROWS - 1 and payload["n_excluded"] == 1
    (oid, row), = payload["excluded"].items()
    assert row["status"] == "capability_missing" and row["coverage_deg"] is None
    errors = [[o["coverage_deg"], o["ripple_db"]] for o in payload["observations"].values()]
    assert payload["reference"] == frozen_reference(errors)
    hashes = {o["physical_metric_spec_hash"] for o in payload["observations"].values()}
    assert hashes == {payload["metric_policy"]["physical_metric_spec_hash"]}
    # idempotent: a rebuild never moves the frozen reference
    again = builders.build_pareto_metrics(service, sid, root=root)
    assert again["idempotent"] and again["artifact"]["sha256"] == result["artifact"]["sha256"]


def _training(service, sid):
    from hornlab_search.bo.data import TrainingSet
    manifest = _payload(service, service.get_artifact_metadata(sid, "training_manifest"))
    meta = service.get_artifact_metadata(sid, "training")
    with np.load(service.store.artifacts / meta["sha256"], allow_pickle=False) as a:
        X, J = np.asarray(a["X"]), np.asarray(a["J"]).reshape(-1, 1)
    return TrainingSet(status="ok", d=manifest["d"], n=manifest["n"], X=X, J=J, Y=-J,
                       Y_phys=None, G=None, ids=tuple(manifest["ids"]),
                       selected_ids=(), excluded_ids=(), elite_ids=(), maximin_ids=(),
                       n_eligible=manifest["n"], n_unique=manifest["n"], n_min=manifest["n_min"],
                       n_max=256, active_keys=tuple(manifest["active_keys"]),
                       projection_version=None, preparation=None, meta=manifest["meta"])


def test_capability_with_bindings_and_insufficient_rows(tmp_path):
    service, sid, root, _ = _study(tmp_path)
    payload = _payload(service, builders.build_pareto_metrics(service, sid, root=root)["artifact"])
    pt = builders.pareto_training_from_artifacts(_training(service, sid), payload)
    cap = capability_status("pareto", pareto_training=pt)
    assert cap["data_status"] == "ok" and cap["frozen_reference"] == payload["reference"]
    small = ParetoTraining(X=pt.X[:3], errors=pt.errors[:3], J=pt.J[:3], ids=pt.ids[:3],
                           geometry_ids=pt.geometry_ids[:3], reference=pt.reference,
                           metric_spec_hash=pt.metric_spec_hash)
    assert capability_status("pareto", pareto_training=small)["data_reason"] == \
        "insufficient_training_data"
    broken = ParetoTraining(**{**small.__dict__, "reference": {}})
    assert capability_status("pareto", pareto_training=broken)["data_status"] == "unavailable"


def test_production_bindings_ok_with_artifact_and_refused_without(tmp_path):
    from hornlab_search.studies.production import pareto_bindings
    service, sid, root, spec = _study(tmp_path)
    builders.build_proposal(service, sid, root=root, spec=spec, policy="pareto", pool=_pool())
    proposal = _payload(service, service.get_artifact_metadata(sid, "proposal"))
    assert proposal["pareto"]["pareto_metrics"] == \
        service.get_artifact_metadata(sid, "pareto_metrics")["sha256"]
    assert pareto_bindings(service, sid)["observations"]
    with pytest.raises(Unavailable, match="pareto_metrics"):
        pareto_bindings(service, sid, {k: v for k, v in proposal.items() if k != "pareto"})
    tampered = dict(proposal, pareto=dict(proposal["pareto"], reference={"ref_point": [0, 0]}))
    with pytest.raises(Unavailable, match="reference"):
        pareto_bindings(service, sid, tampered)


def test_execution_capability_refuses_unsupported_policy_with_reason(tmp_path):
    from hornlab_search.studies.production import PRODUCTION_POLICIES
    assert PRODUCTION_POLICIES == ("scalar", "turbo", "pareto")


def test_evaluator_adds_metric_observation_after_screen_and_keeps_reference(tmp_path):
    from hornlab_search.studies.evaluator import PipelineStudyEvaluator
    service, sid, root, _ = _study(tmp_path)
    payload = _payload(service, builders.build_pareto_metrics(service, sid, root=root)["artifact"])
    training = _training(service, sid)
    pt = builders.pareto_training_from_artifacts(training, payload)
    ev = PipelineStudyEvaluator(None, {"budget": {}}, training_set=training, policy="pareto",
                                pareto_training=pt)
    calls = []
    import hornlab_search.bo.pareto as pareto_mod
    original = pareto_mod.fit_pareto_training
    pareto_mod.fit_pareto_training = lambda data, seed=0: calls.append(data) or \
        type("F", (), {"status": "ok", "reason": "ok"})()
    try:
        x = list(np.full(training.d, 0.5))
        h = payload["metric_policy"]["physical_metric_spec_hash"]
        good = {"kind": "screen", "solve_id": "s1", "outcome": "success", "eligible": True,
                "observed_j": 0.3, "physical_id": "new-1", "x": x, "design_hash": "g-new-1",
                "pareto_metric": {"status": "complete", "physical_metric_spec_hash": h,
                                  "coverage_deg": 1e6, "ripple_db": 1e6}}
        ev.observe(good)
        bad = dict(good, solve_id="s2", physical_id="new-2", design_hash="g-new-2",
                   x=list(np.full(training.d, 0.6)),
                   pareto_metric={"status": "capability_missing", "reason": "no cuts"})
        ev.observe(bad)
    finally:
        pareto_mod.fit_pareto_training = original
    current = ev.current_pareto_training()
    assert "new-1" in current.ids and "new-2" not in current.ids
    assert ev.pareto_excluded["new-2"].startswith("metric observation capability_missing")
    assert current.reference == pt.reference      # a far-worse new row never moves it
    assert good["objectives"] == [1e6, 1e6]
    assert calls and "new-1" in calls[0].ids
    assert "pareto_excluded" in ev.proposal_rng_state()["rng_state"]


def test_frozen_reference_fit_accepts_rows_beyond_reference(tmp_path):
    pytest.importorskip("botorch")
    from hornlab_search.bo.pareto import fit_pareto_training
    rng = np.random.default_rng(0)
    X = rng.random((30, 3))
    errors = np.c_[X[:, 0] * 10 + 1, X[:, 1] * 2 + .5]
    ref = frozen_reference(errors[:-2])
    errors[-1] = [100.0, 100.0]
    pt = ParetoTraining(X=X, errors=errors, J=errors.sum(1), ids=tuple(map(str, range(30))),
                        geometry_ids=tuple(f"g{i}" for i in range(30)), reference=ref,
                        metric_spec_hash="a" * 64)
    fit = fit_pareto_training(pt, seed=0)
    assert fit.status == "ok", fit.reason
    assert fit.reference == ref
