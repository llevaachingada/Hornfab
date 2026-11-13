"""S1/F1: CMA-ME archive identity, failure exclusion and QD infrastructure isolation.

Offline only: no BEM, GPU, mesher or solver. A fake evaluator returns a real ``MetricSet`` and
``Evaluation`` (smooth beamwidths/J from the normalized vector), so the production search loop,
ribs scheduler/emitter, archive subclass and resume/protocol paths are exercised; only the
acoustics is replaced. Archive assertions inspect the actual archive objects and the actual
scheduler/emitter calls.
"""
from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import cma_me as qd_mod
from hornlab_search.search.evaluate import (DETERMINISTIC_KINDS, append_ndjson, error_kind,
                                            evaluation_to_row, read_ndjson, row_to_evaluation)
from hornlab_search.types import Design, Evaluation, MetricSet, SolveOutcome
from test_search_support import LIBS, SyntheticBackend

QD_NAMES = ("mean_bw_h_deg", "mean_bw_v_deg")


# ------------------------------------------------------------------ fixtures / helpers


def qd_block(**kw) -> dict:
    block = {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg",
             "bins_h": 5, "bins_v": 5}
    block.update(kw)
    return block


def two_knob_cfg(smoke, qd=None, *, popsize: int = 2):
    """Smoke family reduced to ``a_deg``/``aspect_ratio`` with a qd block and a fixed batch size."""
    bounds = {k: dict(v) for k, v in smoke.bounds_raw.items()}
    for k in bounds:
        bounds[k]["search"] = k in ("a_deg", "aspect_ratio")
    raw = json.loads(json.dumps(smoke.raw))
    raw["search"] = {**raw["search"], "algorithm": "cma_me", "qd": qd or qd_block(),
                     "popsize": int(popsize)}
    s = dataclasses.replace(smoke.search, algorithm="cma_me", qd=qd or qd_block(),
                            tolfun=1e-12, restarts=None, popsize=int(popsize))
    return dataclasses.replace(smoke, bounds_raw=bounds, search=s, raw=raw)


def strict_cfg(cfg):
    """Add the opt-in error policy the config lane will validate (kept off the dataclass here)."""
    cfg = dataclasses.replace(cfg, search=dataclasses.replace(cfg.search))
    setattr(cfg.search, "error_policy", "retry_same_then_stop")
    return cfg


def fake_eval(cfg, *, fail=None, log=None, metrics_none=None):
    """A caching stand-in for ``evaluate`` using the real evaluation identity.

    ``fail(design, u, call_no) -> error string | None``; ``metrics_none(design, u, call_no)``
    returns a *complete* evaluation with no descriptors (to prove missing descriptors are never
    stored). Rows are written to search.ndjson exactly like the production evaluator; transient
    failures are deliberately NOT memoised, so a retry really re-evaluates.
    """
    freqs = np.linspace(float(cfg.target_raw["band_lo_hz"]), float(cfg.target_raw["band_hi_hz"]), 9)
    calls = {"n": 0}

    def fake(design, space, cfg_, mode, run_dir, store, backend, *, ctx=None, **kw):
        dh, mh, sh, key = qd_mod._evaluation_identity(design, space, cfg_, mode)
        if ctx is not None and key in ctx.known:
            return dataclasses.replace(ctx.known[key], design=design)
        call_no = calls["n"]
        calls["n"] += 1
        try:
            u = np.asarray(space.normalize(design), dtype=float).reshape(-1)
        except Exception:  # noqa: BLE001 - an unnormalisable generated design is a fake failure
            u = np.zeros(max(2, len(space.keys())), dtype=float)
        u1 = float(u[0]) if u.size else 0.0
        u2 = float(u[1]) if u.size > 1 else 1.0 - u1
        error = fail(design, u, call_no) if fail is not None else None
        if error:
            kind = error_kind(error)
            # Deterministic refusals never reach the solver; model the pre-solver outcome as None
            # so the F1 backend-call counter can distinguish them from a real solve failure.
            outcome = (None if kind in DETERMINISTIC_KINDS
                       else SolveOutcome(False, None, 0.0, None, error))
            ev = Evaluation(design_hash=dh, design=design, mesh_hash=mh, solve_hash=sh,
                            objective=1000.0, terms={"total": 1000.0}, metrics=None, mesh=None,
                            outcome=outcome, cached=False, error=error)
        else:
            metrics = None
            if metrics_none is None or not metrics_none(design, u, call_no):
                n = freqs.size
                metrics = MetricSet(
                    freqs_hz=freqs.copy(), bw_h_deg=np.full(n, 180.0 * u1),
                    bw_v_deg=np.full(n, 180.0 * u2), di_db=np.zeros(n),
                    di_source="cuts_estimate", ripple_h_db=np.zeros(n),
                    ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n), z_throat_real=None,
                    scalars={})
            j = float((u1 - 0.62) ** 2 + (u2 - 0.37) ** 2)
            ev = Evaluation(design_hash=dh, design=design, mesh_hash=mh, solve_hash=sh,
                            objective=j, terms={"total": j}, metrics=metrics, mesh=None,
                            outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False,
                            error="")
        if log is not None:
            log.append((dh, error))
        if ctx is not None and run_dir is not None:
            row = evaluation_to_row(ev, mode, ctx.n_rows,
                                    {"mesh": 0.0, "solve": 0.0, "total": 0.0})
            append_ndjson(Path(run_dir) / "search.ndjson", row)
            ctx.n_rows += 1
            if not error or error_kind(error) in DETERMINISTIC_KINDS:
                ctx.known[row["key"]] = row_to_evaluation(row)
        return ev

    return fake


def run_qd(cfg, run_dir, budget, **kw):
    return cma_mod.search(cfg, run_dir, "screen", backend=SyntheticBackend(), budget=budget,
                          lib_shas=LIBS, **kw)


def run_json(run_dir):
    return json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))


def archive_json(run_dir):
    return json.loads((Path(run_dir) / "archive.json").read_text(encoding="utf-8"))


def reduced_space(cfg):
    space = DesignSpace.from_config(cfg)
    space, _ = qd_mod.links_mod.reduce_space(space, cfg)
    return space


def archived_design_hashes(archive, cfg):
    space = reduced_space(cfg)
    data = archive.data()
    out = set()
    for sol in np.asarray(data["solution"]).reshape(len(data["solution"]), -1):
        design = space.denormalize(np.clip(sol, 0.0, 1.0))
        out.add(qd_mod._evaluation_identity(design, space, cfg, "screen")[0])
    return out


def record_archives(monkeypatch):
    """Capture the two archive instances the scheduler receives."""
    made = []
    base = qd_mod.FailureExcludingGridArchive

    class Recording(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(qd_mod, "FailureExcludingGridArchive", Recording)
    return made


def spy_scheduler(monkeypatch):
    from ribs.schedulers import Scheduler
    calls = {"ask": 0, "tell": 0, "told": []}
    real_ask, real_tell = Scheduler.ask, Scheduler.tell

    def ask(self):
        calls["ask"] += 1
        return real_ask(self)

    def tell(self, objective, measures, **fields):
        calls["tell"] += 1
        calls["told"].append({"objective": np.asarray(objective).copy(),
                              "measures": np.asarray(measures).copy(),
                              "eligible": None if "eligible" not in fields
                              else np.asarray(fields["eligible"]).copy()})
        return real_tell(self, objective, measures, **fields)

    monkeypatch.setattr(Scheduler, "ask", ask)
    monkeypatch.setattr(Scheduler, "tell", tell)
    return calls


def spy_emitter(monkeypatch):
    from ribs.emitters import EvolutionStrategyEmitter
    records = []
    real = EvolutionStrategyEmitter.tell

    def tell(self, solution, objective, measures, add_info, **fields):
        records.append({"status": np.asarray(add_info["status"]).copy(),
                        "value": np.asarray(add_info["value"]).copy(),
                        "eligible": None if "eligible" not in fields
                        else np.asarray(fields["eligible"]).copy(),
                        "solution": np.asarray(solution).copy(),
                        "objective": np.asarray(objective).copy()})
        return real(self, solution, objective, measures, add_info, **fields)

    monkeypatch.setattr(EvolutionStrategyEmitter, "tell", tell)
    return records


# ------------------------------------------------------------------ S1 Bug 1: seed identity


def test_warm_mean_differs_from_seed_and_archives_the_evaluated_seed(smoke_cfg, tmp_path,
                                                                     monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=5, bins_v=5))
    seed_params = dict(smoke_cfg.seed_params)
    warm_design = Design("OSSE", {**seed_params, "a_deg": 40.0, "aspect_ratio": 1.70})
    warm_record = {"mean_design_hash": warm_design.hash(), "from_runs": ["fixture"],
                   "mean_objective": 0.0, "sigma0": 0.2}
    monkeypatch.setattr(qd_mod.warmstart, "mean_and_sigma", lambda cfg_, space: (warm_design,
                                                                                warm_record))

    captured = {}
    from ribs.emitters import EvolutionStrategyEmitter as RealEmitter

    class RecordingEmitter(RealEmitter):
        def __init__(self, *args, **kwargs):
            captured["x0"] = np.asarray(kwargs.get("x0"), dtype=float).copy()
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("ribs.emitters.EvolutionStrategyEmitter", RecordingEmitter)
    made = record_archives(monkeypatch)

    log = []
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, log=log))
    run_qd(cfg, tmp_path / "r", 1)          # seed only: the archive round-trip

    space = reduced_space(cfg)
    x_seed = space.normalize(space.seed)
    x_warm = space.normalize(warm_design)
    assert not np.allclose(x_seed, x_warm), "fixture must distinguish seed from warm mean"
    assert np.allclose(captured["x0"], x_warm), "the emitter mean must stay the warm x0"

    a = archive_json(tmp_path / "r")
    assert len(a["cells"]) == 1
    assert a["stats"]["total_evals"] == 1 and a["stats"]["non_cached"] == 1
    cell = a["cells"][0]
    assert cell["design_hash"] == space.seed.hash()
    assert cell["design_hash"] != warm_design.hash()
    seed_j = float((x_seed[0] - 0.62) ** 2 + (x_seed[1] - 0.37) ** 2)
    warm_j = float((x_warm[0] - 0.62) ** 2 + (x_warm[1] - 0.37) ** 2)
    assert cell["objective"] == pytest.approx(seed_j)
    assert not math.isclose(seed_j, warm_j, rel_tol=1e-6, abs_tol=1e-9)
    assert not np.allclose([180.0 * x_seed[0], 180.0 * x_seed[1]],
                           [180.0 * x_warm[0], 180.0 * x_warm[1]])
    # the evaluated normalized seed vector, not the warm x0, is what the archive stores
    assert len(made) == 2
    assert np.allclose(np.asarray(made[0].data()["solution"]), x_seed[None])
    assert not np.allclose(np.asarray(made[0].data()["solution"]), x_warm[None])
    assert log == [(space.seed.hash(), None)]


def test_links_reduced_space_archives_the_evaluated_normalized_seed(smoke_cfg, tmp_path,
                                                                    monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4))
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    # validated link that removes aspect_ratio from the search dimension
    cfg.search.links = {"aspect_ratio": {"from": "a_deg", "scale": 0.02, "offset": 0.0,
                                         "min": 1.0, "max": 2.0}}
    made = record_archives(monkeypatch)
    run_qd(cfg, tmp_path / "r", 1)

    space = reduced_space(cfg)
    assert len(space.keys()) == 1
    x_seed = space.normalize(space.seed)
    linked_hash = qd_mod._evaluation_identity(space.seed, space, cfg, "screen")[0]
    a = archive_json(tmp_path / "r")
    assert len(a["cells"]) == 1
    assert a["cells"][0]["design_hash"] == linked_hash
    assert len(made) == 2
    assert np.allclose(np.asarray(made[0].data()["solution"]), x_seed[None])


def test_generated_space_seed_is_archived_and_links_are_refused(tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = load_config(EXAMPLES / "typologies" / "grid_ellipse.yaml")
    s = dataclasses.replace(cfg.search, algorithm="cma_me", qd=qd_block(bins_h=4, bins_v=4),
                            tolfun=1e-12, restarts=None, popsize=2)
    cfg = dataclasses.replace(cfg, search=s)
    space = DesignSpace.from_config(cfg)
    assert space.__class__.__name__ == "GeneratedSpace"

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    made = record_archives(monkeypatch)
    run_qd(cfg, tmp_path / "g", 1)
    x_seed = space.normalize(space.seed)
    a = archive_json(tmp_path / "g")
    assert len(a["cells"]) == 1
    assert len(made) == 2
    assert np.allclose(np.asarray(made[0].data()["solution"]), x_seed[None])

    # GeneratedSpace + links is refused (not silently applied to a generator block).
    cfg2 = dataclasses.replace(cfg, search=dataclasses.replace(cfg.search))
    cfg2.search.links = {"L_mm": {"from": "h_rm_mm", "scale": 1.0, "offset": 0.0,
                                  "min": 50.0, "max": 400.0}}
    with pytest.raises(ValueError, match="generator"):
        run_qd(cfg2, tmp_path / "gl", 1)


def test_failed_or_descriptorless_seed_is_not_archived(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    made = record_archives(monkeypatch)
    # failed seed: neither archive gets it, and it is not a "best"
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4))
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg, fail=lambda d, u, n: "invalid_geometry: fixture" if n == 0
                                  else None))
    run_qd(cfg, tmp_path / "failed", 1)
    a = archive_json(tmp_path / "failed")
    assert a["cells"] == [] and a["stats"]["occupied_bins"] == 0
    rj = run_json(tmp_path / "failed")
    assert rj["seed"]["design_hash"]                 # baseline is recorded under seed only
    assert "best" not in rj
    assert not (tmp_path / "failed" / "best.json").exists()
    assert len(made) == 2 and all(len(arc) == 0 for arc in made)

    # complete seed with no metrics/descriptors: also neither archive, also not best
    cfg2 = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4))
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg2, metrics_none=lambda d, u, n: n == 0))
    run_qd(cfg2, tmp_path / "nodesc", 1)
    a2 = archive_json(tmp_path / "nodesc")
    assert a2["cells"] == [] and a2["stats"]["occupied_bins"] == 0
    heat = json.loads((tmp_path / "nodesc" / "archive_heatmap.json").read_text(encoding="utf-8"))
    assert heat["cells"] == []
    assert "best" not in run_json(tmp_path / "nodesc")
    assert not (tmp_path / "nodesc" / "best.json").exists()
    assert len(made) == 4 and all(len(arc) == 0 for arc in made[2:])


def test_complete_seed_is_the_shared_baseline_of_both_archives(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4))
    made = record_archives(monkeypatch)
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, tmp_path / "r", 1)
    assert len(made) == 2 and made[0] is not made[1]
    space = reduced_space(cfg)
    x_seed = space.normalize(space.seed)
    for arc in made:
        assert len(arc) == 1, "both archives must contain the complete seed cell"
        assert np.allclose(np.asarray(arc.data()["solution"]), x_seed[None])
    assert np.allclose(np.asarray(made[0].data()["objective"]),
                       np.asarray(made[1].data()["objective"]))


def test_failed_seed_is_not_best_until_a_complete_candidate(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    qd = qd_block(bins_h=4, bins_v=4)
    log = []

    # budget=1, failing seed: no best at all
    cfg = two_knob_cfg(smoke_cfg, qd=qd, popsize=2)
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg, fail=lambda d, u, n: "invalid_geometry: fixture" if n == 0
                                  else None, log=log))
    run_qd(cfg, tmp_path / "one", 1)
    rj = run_json(tmp_path / "one")
    assert rj["seed"]["design_hash"] and "best" not in rj
    assert not (tmp_path / "one" / "best.json").exists()

    # a later complete candidate becomes best; the failed seed never does
    log.clear()
    cfg2 = two_knob_cfg(smoke_cfg, qd=qd, popsize=2)
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg2, fail=lambda d, u, n: "invalid_geometry: fixture" if n == 0
                                  else None, log=log))
    run_qd(cfg2, tmp_path / "later", 4)
    rj2 = run_json(tmp_path / "later")
    assert rj2["seed"]["design_hash"]
    assert rj2["best"]["design_hash"] != rj2["seed"]["design_hash"]
    successful = {dh for dh, err in log if not err}
    assert rj2["best"]["design_hash"] in successful
    assert rj2["best"]["objective"] < 1000.0
    assert (tmp_path / "later" / "best.json").exists()



# ------------------------------------------------------------------ S1 Bug 2: archive admission


def me_archive():
    return qd_mod.FailureExcludingGridArchive(
        solution_dim=2, dims=[4, 4],
        ranges=[qd_mod.DESCRIPTOR_RANGE_DEG, qd_mod.DESCRIPTOR_RANGE_DEG], seed=0)


def mae_archive(j_threshold, *, learning_rate=0.1):
    return qd_mod.FailureExcludingGridArchive(
        solution_dim=2, dims=[4, 4],
        ranges=[qd_mod.DESCRIPTOR_RANGE_DEG, qd_mod.DESCRIPTOR_RANGE_DEG],
        learning_rate=learning_rate, threshold_min=-float(j_threshold), seed=0)


@pytest.mark.parametrize("label,archive_factory,admit_success", [
    ("me", me_archive, True),
    ("mae999", lambda: mae_archive(999.0), True),
    ("mae1000", lambda: mae_archive(1000.0), True),
    ("mae1500", lambda: mae_archive(1500.0), True),
    ("maeinf", lambda: mae_archive(float("inf"), learning_rate=1.0), True),
    ("maenan", lambda: mae_archive(float("nan")), False),
])
def test_failures_are_never_admitted_at_any_threshold(label, archive_factory, admit_success):
    arc = archive_factory()
    sol = np.asarray([[0.2, 0.3]], dtype=float)
    meas = np.asarray([[90.0, 90.0]], dtype=float)
    # an empty cell must not accept a -1000 failure
    info = arc.add(solution=sol, objective=np.asarray([-1000.0]), measures=meas,
                   eligible=np.asarray([False]))
    assert info["status"].tolist() == [0]
    assert np.isfinite(info["value"]).all()
    assert len(arc) == 0

    # mixed batch: failure and success in the same cell; only the eligible row may be admitted
    info = arc.add(solution=np.asarray([[0.20, 0.30], [0.21, 0.31]], dtype=float),
                   objective=np.asarray([-1000.0, -50.0]),
                   measures=np.asarray([[90.0, 90.0], [90.0, 90.0]], dtype=float),
                   eligible=np.asarray([False, True]))
    assert info["status"].tolist()[0] == 0          # never 1/2 for a failure
    assert np.isfinite(info["value"]).all()
    assert info["value"][0] < info["value"][1]      # excluded ranks strictly last
    if admit_success:
        assert info["status"].tolist()[1] in (1, 2)
        assert len(arc) == 1
        stored = np.asarray(arc.data()["objective"], dtype=float)
        assert np.all(stored > -999.0), "failure objective was stored"
    else:
        assert len(arc) == 0


def test_large_successful_objective_is_admitted_and_only_mask_decides():
    arc = me_archive()
    meas = np.asarray([[90.0, 90.0]], dtype=float)
    ok = arc.add(solution=np.asarray([[0.2, 0.3]], dtype=float),
                 objective=np.asarray([-1500.0]), measures=meas, eligible=np.asarray([True]))
    assert ok["status"].tolist() == [2] and len(arc) == 1
    # the same large objective is excluded when the evaluation is not complete
    arc2 = me_archive()
    bad = arc2.add(solution=np.asarray([[0.2, 0.3]], dtype=float),
                   objective=np.asarray([-1500.0]), measures=meas, eligible=np.asarray([False]))
    assert bad["status"].tolist() == [0] and len(arc2) == 0
    # a genuine large J above the MAE threshold is admitted
    arc3 = mae_archive(2000.0)
    ok3 = arc3.add(solution=np.asarray([[0.2, 0.3]], dtype=float),
                   objective=np.asarray([-1500.0]), measures=meas, eligible=np.asarray([True]))
    assert ok3["status"].tolist() == [2] and len(arc3) == 1


def test_duplicate_identities_in_one_batch_occupy_one_cell():
    arc = me_archive()
    meas = np.asarray([[90.0, 90.0], [90.0, 90.0]], dtype=float)
    info = arc.add(solution=np.asarray([[0.2, 0.3], [0.2, 0.3]], dtype=float),
                   objective=np.asarray([-10.0, -5.0]), measures=meas,
                   eligible=np.asarray([True, True]))
    assert len(arc) == 1
    assert info["status"].tolist() == [2, 2]     # both "discover" the cell; only max is stored
    assert np.asarray(arc.data()["objective"])[0] == pytest.approx(-5.0)


@pytest.mark.parametrize("maes", [None, {"learning_rate": 0.1, "j_threshold": 1500.0}])
def test_search_excludes_failures_from_both_archives(smoke_cfg, tmp_path, monkeypatch, maes):
    pytest.importorskip("ribs", reason="ribs not installed")
    qd = qd_block(bins_h=5, bins_v=5, **({"maes": maes} if maes else {}))
    cfg = two_knob_cfg(smoke_cfg, qd=qd, popsize=2)
    made = record_archives(monkeypatch)
    records = spy_emitter(monkeypatch)
    log = []

    def fail(design, u, call_no):
        # seed ok; every second candidate is a deterministic refusal (classic ME empty-cell bug)
        return "invalid_geometry: fixture" if call_no % 2 == 1 and call_no != 0 else None

    def no_metrics(design, u, call_no):
        return call_no == 2                 # complete but descriptorless: must not be stored

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, fail=fail, log=log,
                                                       metrics_none=no_metrics))
    run_qd(cfg, tmp_path / "r", 9)

    failed = {dh for dh, err in log if err}
    # call 0 = seed, call 1 = first deterministic refusal, call 2 = descriptorless success
    descriptorless = {log[2][0]} if len(log) > 2 else set()
    assert failed and descriptorless and not (failed & descriptorless)

    assert len(made) == 2, "the scheduler must receive distinct search and result archives"
    assert made[0] is not made[1]
    for arc in made:
        hashes = archived_design_hashes(arc, cfg)
        assert not (hashes & failed), f"failure stored as an elite in {arc!r}"
        assert not (hashes & descriptorless), "descriptorless design stored"
        stored_obj = np.asarray(arc.data()["objective"], dtype=float)
        assert np.all(np.isfinite(stored_obj))
    assert len(made[1]) > 0, "the result archive should hold eligible successes"

    assert records
    for rec in records:
        eligible = rec["eligible"]
        assert eligible is not None
        assert np.all(rec["status"][~eligible] == 0)
        assert not np.any(rec["status"][~eligible] == 1)
        assert not np.any(rec["status"][~eligible] == 2)

    # archive.json advertises only eligible cells (never the failure penalty)
    a = archive_json(tmp_path / "r")
    assert all(c["objective"] > -999.0 for c in a["cells"])
    rj = run_json(tmp_path / "r")
    assert rj["qd"]["protocol"] == qd_mod.QD_PROTOCOL
    assert rj["qd"]["failure_exclusion"]["search_archive"] is True
    assert rj["qd"]["failure_exclusion"]["result_archive"] is True
    assert rj["qd"]["failure_exclusion"]["mae_feasible_only"] is False
    assert rj["qd"]["deterministic_refusal_policy"] == qd_mod.QD_DETERMINISTIC_REFUSAL_POLICY
    assert rj["qd"]["total_bins"] == 25


# ------------------------------------------------------------------ F1: infrastructure policy


def test_transient_then_success_matches_the_healthy_told_trajectory(smoke_cfg, tmp_path,
                                                                    monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    qd = qd_block(bins_h=4, bins_v=4)

    healthy_cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd, popsize=2))
    records = spy_emitter(monkeypatch)
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(healthy_cfg))
    run_qd(healthy_cfg, tmp_path / "healthy", 6)
    healthy = [(r["solution"].copy(), r["objective"].copy()) for r in records]

    failing_cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd, popsize=2))
    records.clear()
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(failing_cfg,
                                  fail=lambda d, u, n: "solve_failed: fixture" if n == 1 else None))
    run_qd(failing_cfg, tmp_path / "transient", 6)
    failing = [(r["solution"].copy(), r["objective"].copy()) for r in records]

    assert len(healthy) == len(failing) > 0
    for (hx, ho), (fx, fo) in zip(healthy, failing):
        assert np.allclose(hx, fx) and np.allclose(ho, fo)
    assert run_json(tmp_path / "transient")["stop_reason"] == "budget"


def test_error_policy_stats_count_backend_calls_and_retries(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=3))

    # First invocation: seed + one candidate only (partial generation, no tell).
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, tmp_path / "r", 2)
    pending = json.loads((tmp_path / "r" / "qd" / "pending_batch.json").read_text())
    assert pending["generation"] == 0
    assert [bool(r["dispatched"]) for r in pending["vectors"]] == [True, False, False]
    assert run_json(tmp_path / "r")["qd"]["error_policy_stats"]["backend_calls"] == 2

    # Resume batch: candidate 0 is a cache hit, candidate 1 is a deterministic pre-solver
    # refusal (no backend call), candidate 2 is transient then succeeds (two backend calls).
    calls = spy_scheduler(monkeypatch)
    emitted = spy_emitter(monkeypatch)
    log = []

    def fail(design, u, call_no):
        if call_no == 0:
            return "invalid_geometry: fixture"
        if call_no == 1:
            return "solve_failed: fixture"
        return None

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, log=log, fail=fail))
    run_qd(cfg, None, 5, resume=tmp_path / "r")

    stats = run_json(tmp_path / "r")["qd"]["error_policy_stats"]
    # Cumulative across the resume: the first invocation's seed + first candidate spent 2 backend
    # calls; the replay of those rows is free (seed and candidate 0 are cache hits), so this
    # invocation adds the deterministic refusal (0), the transient attempt + retry (2), the
    # completed generation's next candidate (1) and the next generation's first candidate (1).
    # Total 5, never a fresh per-invocation ledger.
    assert stats == {"backend_calls": 5, "retries": 1, "transient_failures": 1,
                     "metric_failures": 0, "unknown_failures": 0}
    assert calls["ask"] == 2 and calls["tell"] == 1
    assert len(emitted) == 1
    told_solutions = emitted[0]["solution"]
    assert len(told_solutions) == 3        # cached + refused + retried candidate
    target = np.asarray(pending["vectors"][2]["unit_vector"], dtype=float)
    assert np.sum(np.all(np.isclose(told_solutions, target), axis=1)) == 1
    assert [err for _, err in log] == ["invalid_geometry: fixture", "solve_failed: fixture",
                                       None, None]




@pytest.mark.parametrize("error,reason", [
    ("solve_failed: fixture", "qd_infrastructure"),
    ("metrics_failed: fixture", "qd_metric_error"),
    ("RuntimeError: fixture", "qd_unknown_error"),
])
def test_strict_policy_stops_before_tell(smoke_cfg, tmp_path, monkeypatch, error, reason):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    calls = spy_scheduler(monkeypatch)
    log = []

    def fail(design, u, call_no):
        return error if call_no >= 1 else None    # seed succeeds; first candidate is the failure

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, fail=fail, log=log))
    run_qd(cfg, tmp_path / "r", 6)

    rj = run_json(tmp_path / "r")
    assert rj["stop_reason"].startswith(reason), rj["stop_reason"]
    assert calls["tell"] == 0       # the failed batch is not told; the seed is added directly
    assert calls["ask"] == 1
    pending = json.loads((tmp_path / "r" / "qd" / "pending_batch.json").read_text())
    assert pending["protocol"] == qd_mod.QD_PROTOCOL
    assert pending["vectors"][0]["dispatched"] is True
    if error.startswith("solve_failed"):
        assert pending["vectors"][0]["attempts"] == 2       # same-candidate retry, no new ask
        assert log.count((log[1][0], error)) == 2
    else:
        assert pending["vectors"][0]["attempts"] == 1
    # the seed is still the only elite (seed success is archived directly)
    assert archive_json(tmp_path / "r")["stats"]["occupied_bins"] == 1


def test_persistent_transient_resume_reconciles_durable_failure_and_completes(smoke_cfg,
                                                                             tmp_path, monkeypatch):
    """A durable failure row resolves the dispatched pending intent, so the deterministic replay
    re-enters the SAME candidate (it is not memoised) instead of refusing every later resume."""
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg, fail=lambda d, u, n: "solve_failed: fixture"
                                  if n >= 1 else None))
    run_qd(cfg, rd, 5)
    assert run_json(rd)["stop_reason"].startswith("qd_infrastructure")
    pending = json.loads((rd / "qd" / "pending_batch.json").read_text())
    stuck = next(r for r in pending["vectors"] if r["dispatched"])
    stuck_hash = stuck["design_hash"]
    # the aborted attempt wrote durable failure row(s): exactly the evidence reconciliation uses
    assert any(r.get("design_hash") == stuck_hash and r.get("kind") == "solve_failed"
               for r in read_ndjson(rd / "search.ndjson"))

    calls = spy_scheduler(monkeypatch)
    resumed_log = []
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, log=resumed_log))
    run_qd(cfg, None, 5, resume=rd)

    rj = run_json(rd)
    assert not rj["stop_reason"].startswith("unknown_pending_attempt")
    assert rj["stop_reason"] == "budget", rj["stop_reason"]
    assert calls["ask"] > 0 and calls["tell"] > 0
    assert not (rd / "qd" / "pending_batch.json").exists()
    # the same candidate was re-dispatched and succeeded on the healthy backend
    assert any(dh == stuck_hash for dh, err in resumed_log if not err)
    assert any(r.get("design_hash") == stuck_hash and r.get("ok")
               for r in read_ndjson(rd / "search.ndjson"))
    assert rj["qd"]["strict"]["counters"]["new"] == 5
    assert archive_json(rd)["stats"]["occupied_bins"] >= 2


def test_pending_without_a_durable_row_dispatches_nothing(smoke_cfg, tmp_path, monkeypatch):
    """A dispatched intent with NO durable row at all is a true unknown attempt: refuse dispatch."""
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate",
                        fake_eval(cfg, fail=lambda d, u, n: "solve_failed: fixture"
                                  if n >= 1 else None))
    run_qd(cfg, rd, 6)
    assert run_json(rd)["stop_reason"].startswith("qd_infrastructure")
    pending = json.loads((rd / "qd" / "pending_batch.json").read_text())
    stuck = next(r for r in pending["vectors"] if r["dispatched"])
    # Simulate a missing/torn durable write for that attempt: drop every row with its identity.
    keep = [r for r in read_ndjson(rd / "search.ndjson")
            if not (r.get("design_hash") == stuck["design_hash"]
                    and r.get("mesh_hash") == stuck["mesh_hash"]
                    and r.get("solve_hash") == stuck["solve_hash"])]
    (rd / "search.ndjson").write_text(
        "".join(json.dumps(r) + "\n" for r in keep), encoding="utf-8")

    calls = spy_scheduler(monkeypatch)
    evaluations = []

    def forbidden(*args, **kwargs):
        evaluations.append(1)
        raise AssertionError("evaluate must not run over unresolved pending state")

    monkeypatch.setattr(qd_mod, "evaluate", forbidden)
    run_qd(cfg, None, 6, resume=rd)
    assert evaluations == []
    assert calls["ask"] == 0 and calls["tell"] == 0
    assert run_json(rd)["stop_reason"].startswith("unknown_pending_attempt")


def test_partial_generation_resume_replays_to_the_uninterrupted_archive(smoke_cfg, tmp_path,
                                                                         monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    qd = qd_block(bins_h=4, bins_v=4)
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd, popsize=4))

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, tmp_path / "whole", 6)
    whole = archive_json(tmp_path / "whole")

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, tmp_path / "r", 3)              # seed + two of four candidates; no tell
    pending = json.loads((tmp_path / "r" / "qd" / "pending_batch.json").read_text())
    assert pending["generation"] == 0
    assert sum(bool(r["dispatched"]) for r in pending["vectors"]) == 2
    assert run_json(tmp_path / "r")["stop_reason"] == "budget"

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    # An explicit larger budget is required: the cumulative counters/caps are restored, so the
    # same budget would stop immediately. The extension finishes the replayed generation and one
    # later generation, exactly like the uninterrupted run.
    run_qd(cfg, None, 6, resume=tmp_path / "r")
    resumed = archive_json(tmp_path / "r")
    assert resumed["cells"] == whole["cells"]
    for key in ("total_bins", "occupied_bins", "coverage", "non_cached"):
        assert resumed["stats"][key] == whole["stats"][key]
    st = run_json(tmp_path / "r")["qd"]["strict"]
    assert st["extensions"] == [{"cap": "budget", "from": 3, "to": 6}]
    assert st["counters"]["new"] == 6
    assert not run_json(tmp_path / "r")["stop_reason"].startswith("unknown_pending_attempt")


def _strict_max_attempts(cfg, value: int):
    cfg = strict_cfg(cfg)
    setattr(cfg.search, "max_attempts", int(value))
    return cfg


def test_resume_after_budget_stop_cannot_exceed_the_stored_cap(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, rd, 3)                       # seed + one full 2-candidate generation
    rows_before = len(read_ndjson(rd / "search.ndjson"))
    assert run_json(rd)["qd"]["strict"]["counters"]["new"] == 3

    calls = spy_scheduler(monkeypatch)
    resumed_log = []
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, log=resumed_log))
    run_qd(cfg, None, 3, resume=rd)          # same budget: the stored cap is spent

    assert run_json(rd)["stop_reason"] == "budget"
    assert calls["ask"] == 0 and calls["tell"] == 0
    assert resumed_log == []
    assert len(read_ndjson(rd / "search.ndjson")) == rows_before
    st = run_json(rd)["qd"]["strict"]
    assert st["counters"]["new"] == 3 and st["counters"]["attempts"] == 3
    assert st["extensions"] == []


def test_resume_records_and_honors_an_explicit_larger_budget(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, rd, 3)

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, None, 5, resume=rd)          # explicit extension 3 -> 5
    rj = run_json(rd)
    assert rj["stop_reason"] == "budget"
    st = rj["qd"]["strict"]
    assert st["extensions"] == [{"cap": "budget", "from": 3, "to": 5}]
    assert st["caps"]["budget"] == 5
    assert st["counters"]["new"] == 5
    # the resumable artifact carries the same cumulative ledger
    on_disk = json.loads((rd / "qd" / "strict_state.json").read_text())
    assert on_disk["counters"]["new"] == 5
    assert on_disk["extensions"] == [{"cap": "budget", "from": 3, "to": 5}]


def test_resume_counters_are_not_double_counted_and_second_resume_spends_nothing(
        smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, rd, 3)

    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, None, 5, resume=rd)
    first = run_json(rd)["qd"]["strict"]["counters"]
    assert first["new"] == 5 and first["attempts"] == 5

    # A third invocation with no further extension spends nothing and must not re-count the
    # replayed cached prefix (new/attempts stay 5, not 10).
    calls = spy_scheduler(monkeypatch)
    resumed_log = []
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg, log=resumed_log))
    run_qd(cfg, None, 5, resume=rd)
    second = run_json(rd)["qd"]["strict"]["counters"]
    assert second == first
    assert resumed_log == []
    assert calls["ask"] == 0 and calls["tell"] == 0
    assert run_json(rd)["qd"]["strict"]["extensions"] == [
        {"cap": "budget", "from": 3, "to": 5}]


def test_resume_records_and_honors_an_explicit_larger_attempts_cap(smoke_cfg, tmp_path,
                                                                  monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = _strict_max_attempts(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4),
                                            popsize=2), 3)
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, rd, 100)                    # the attempt cap, not the budget, stops the run
    assert run_json(rd)["qd"]["strict"]["counters"]["attempts"] == 3

    cfg2 = _strict_max_attempts(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4),
                                             popsize=2), 5)
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg2))
    run_qd(cfg2, None, 100, resume=rd)
    st = run_json(rd)["qd"]["strict"]
    assert st["extensions"] == [{"cap": "attempts_cap", "from": 3, "to": 5}]
    assert st["caps"]["attempts_cap"] == 5
    assert st["counters"]["attempts"] == 5


def test_shrinking_a_cumulative_cap_refuses_resume(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=2))
    rd = tmp_path / "r"
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, rd, 5)

    with pytest.raises(ConfigError, match="shrink"):
        run_qd(cfg, None, 3, resume=rd)


def test_protocol_mismatch_and_missing_protocol_are_refused(tmp_path, monkeypatch):
    cfg = two_knob_cfg(load_config(EXAMPLES / "search_smoke.yaml"))
    for i, qd in enumerate(({"protocol": "old-protocol"}, {})):
        run_dir = tmp_path / f"old{i}"
        run_dir.mkdir()
        (run_dir / "run.json").write_text(json.dumps({"qd": qd}), encoding="utf-8")
        with pytest.raises(ConfigError, match="protocol"):
            qd_mod.search(cfg, run_dir, "screen", backend=SyntheticBackend(), budget=1,
                          lib_shas=LIBS)
        assert not (run_dir / "search.ndjson").exists()


def test_budget_on_the_final_slot_tells_once(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = strict_cfg(two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4), popsize=4))
    calls = spy_scheduler(monkeypatch)
    monkeypatch.setattr(qd_mod, "evaluate", fake_eval(cfg))
    run_qd(cfg, tmp_path / "r", 5)              # seed + one full generation
    assert calls["tell"] == 1
    a = archive_json(tmp_path / "r")
    assert a["stats"]["occupied_bins"] >= 2
    assert not (tmp_path / "r" / "qd" / "pending_batch.json").exists()
    assert run_json(tmp_path / "r")["stop_reason"] == "budget"
