"""CPU-only regression checks for rolled-family execution bindings."""
import dataclasses
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.data import materialize_geometry, materialized_geometry_hash
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build as mesh_build, grid_build
from hornlab_search.search import cma as cma_mod, cma_me as qd_mod
from hornlab_search.studies.package import EXECUTION_CODE_FILES, package_hash
from hornlab_search.studies.production import execution_capability
from hornlab_search.studies.evaluator import PipelineStudyEvaluator
from hornlab_search.types import Evaluation, MetricSet, SolveOutcome
from test_search_support import LIBS, SyntheticBackend
from test_study_production import _prepared

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [ROOT / f"examples/typologies/rolled_family_2026-11-15/rf__{kind}_radial_v7.yaml"
           for kind in ("section", "rect")]

FAMILY_SOURCES = {
    "hornlab_search/design/generators/rolled_family.py",
    "hornlab_search/design/generators/_rolled_rect_v1.py",
    "hornlab_search/design/generators/_crowe_section_v2.py",
    "hornlab_search/design/generators/data/crowe_section_reference_v1.yaml",
}


@pytest.mark.parametrize("change", ["missing", "changed"])
@pytest.mark.parametrize("source", sorted(FAMILY_SOURCES))
def test_execution_refuses_missing_or_changed_family_input(tmp_path, monkeypatch, source, change):
    service, package, _ = _prepared(tmp_path, monkeypatch)
    assert FAMILY_SOURCES <= set(EXECUTION_CODE_FILES)
    assert FAMILY_SOURCES <= set(package["code_pins"])
    if change == "missing":
        del package["code_pins"][source]
    else:
        package["code_pins"][source] = "0" * 64
    package["package_id"] = package_hash(package)
    status = execution_capability(service, package, root=tmp_path)
    assert status["status"] == "capability_missing"
    assert source in status["detail"]


@pytest.mark.parametrize("algorithm", ["cma", "cma_me", "cma_mae"])
@pytest.mark.parametrize("config_path", CONFIGS, ids=["section", "rect"])
def test_search_evaluator_resolves_same_geometry_in_fresh_process(tmp_path, monkeypatch, algorithm,
                                                                    config_path):
    """Exercise both real search loops with a fake evaluator, without a GPU or mesher."""
    cfg = load_config(config_path)
    qd = {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg",
          "bins_h": 4, "bins_v": 4}
    if algorithm == "cma_mae":
        qd["maes"] = {"learning_rate": 0.05, "j_threshold": 20.0}
    cfg = dataclasses.replace(cfg, search=dataclasses.replace(
        cfg.search, algorithm="cma_me" if algorithm == "cma_mae" else algorithm,
        qd=qd if algorithm != "cma" else None,
        tolfun=1e-12, restarts=None, popsize=4))
    seen = []
    asks = []
    tells = []
    if algorithm == "cma_mae":
        import ribs.emitters
        real_emitter = ribs.emitters.EvolutionStrategyEmitter

        class CheckingEmitter(real_emitter):
            def __init__(self, *args, **kwargs):
                assert kwargs["bounds"] == [(0.0, 1.0)] * len(kwargs["x0"])
                super().__init__(*args, **kwargs)

            def ask(self):
                batch = super().ask()
                assert np.all((batch >= 0.0) & (batch <= 1.0))
                asks.append(batch.copy())
                return batch

            def tell(self, *args, **kwargs):
                tells.append(True)
                return super().tell(*args, **kwargs)

        monkeypatch.setattr(ribs.emitters, "EvolutionStrategyEmitter", CheckingEmitter)
    script = """
import json, sys
from hornlab_search.bo.data import materialize_geometry, materialized_geometry_hash
from hornlab_search.config import load_config
from hornlab_search.types import Design
cfg = load_config(sys.argv[1])
design = Design('FREEFORM', json.load(sys.stdin))
print(materialized_geometry_hash(materialize_geometry(design, cfg)))
"""

    def capture_grid(geometry, mesh, path, config, **kwargs):
        return geometry

    monkeypatch.setattr(grid_build, "build_grid_mesh", capture_grid)

    def fake(design, space, config, mode, run_dir, store, backend, *, ctx=None, **kwargs):
        materialized = materialize_geometry(design, config)
        local = materialized_geometry_hash(materialized)
        mesh_geometry = mesh_build._build_grid_mesh(design, None, config, run_dir, mode=mode)
        np.testing.assert_array_equal(mesh_geometry["inner_points"], materialized["inner_points"])
        np.testing.assert_array_equal(mesh_geometry["outer_points"], materialized["outer_points"])
        child = subprocess.run([sys.executable, "-c", script, str(config_path)],
                               input=json.dumps(design.params), text=True, capture_output=True,
                               cwd=ROOT, check=True, timeout=60).stdout.strip().splitlines()[-1]
        assert child == local
        seen.append((design.hash(), local))
        n = 3
        metrics = MetricSet(freqs_hz=np.array([500., 1000., 2000.]),
                            bw_h_deg=np.full(n, 90.), bw_v_deg=np.full(n, 60.),
                            di_db=np.zeros(n), di_source="cuts_estimate",
                            ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n),
                            on_axis_db=np.zeros(n), z_throat_real=None, scalars={})
        return Evaluation(design.hash(), design, "mock-mesh", "mock-solve", 1.0,
                          {"total": 1.0}, metrics, None,
                          SolveOutcome(True, None, 0.0, None, ""), cached=False, error="")

    monkeypatch.setattr(qd_mod if algorithm != "cma" else cma_mod, "evaluate", fake)
    seed = DesignSpace.from_config(cfg).seed
    expected = materialized_geometry_hash(materialize_geometry(seed, cfg))
    cma_mod.search(cfg, tmp_path / algorithm, "screen", backend=SyntheticBackend(),
                   budget=6 if algorithm == "cma_mae" else 2,
                   lib_shas=LIBS)
    assert seen and seen[0] == (seed.hash(), expected)
    if algorithm == "cma_mae":
        assert asks and tells
        assert json.loads((tmp_path / algorithm / "run.json").read_text())["qd"]["maes"] == qd["maes"]


@pytest.mark.parametrize("config_path", CONFIGS, ids=["section", "rect"])
def test_family_geometry_identity_survives_cold_resume(config_path):
    cfg = load_config(config_path)
    space = DesignSpace.from_config(cfg)
    design = space.seed
    geom = materialized_geometry_hash(materialize_geometry(design, cfg))
    raw = {"candidate_id": "seed", "geometry_hash": geom, "design_hash": design.hash(),
           "intended_solve_hash": "solve", "params": design.params,
           "active_vector": space.normalize(design).tolist()}
    make = lambda: PipelineStudyEvaluator(None, {"budget": {"screen_calls": 2}},
                                          config=cfg, space=space,
                                          propose_fn=lambda state: raw)
    live = make()
    candidate = live.next_candidate({"screen_calls": 0})
    ev = Evaluation(design.hash(), design, "mesh", "solve", 1.0, {"total": 1.0},
                    None, None, SolveOutcome(True, None, 0.0, None, ""),
                    cached=False, error="")
    result = live.result_from_evaluation(candidate, ev)
    assert result["geometry_hash"] == geom
    assert live.observe(result)
    assert next(iter(live.observations.values())).geometry_hash == geom
    assert geom in live.history.excluded_geometry_hashes

    # Replay a historical result whose result field used the design hash: its
    # separately journaled validated candidate carries the real surface hash.
    old_result = {**result, "geometry_hash": design.hash()}
    resumed = make()
    progress = {"proposal_index": 1, "rng_state": live.proposal_rng_state(),
                "observations": [{"candidate": candidate, "result": old_result}]}
    assert resumed.restore_progress(progress)
    assert next(iter(resumed.observations.values())).geometry_hash == geom
    assert geom in resumed.history.excluded_geometry_hashes


def test_only_explicit_historical_surface_hashes_seed_exclusions_on_resume():
    training = SimpleNamespace(status="ok", X=np.array([[0.2], [0.4]]),
                               J=np.array([1., 2.]), Y_phys=None, ids=("family", "native"),
                               meta={"identities": {
                                   "family": {"design_hash": "family-design",
                                              "geometry_hash": "family-surface"},
                                   "native": {"design_hash": "native-design"}}})
    live = PipelineStudyEvaluator(None, {}, training_set=training)
    assert live.history.excluded_geometry_hashes == ("family-surface",)
    assert live._initial_observations["family"].geometry_hash == "family-surface"
    assert live._initial_observations["native"].geometry_hash == "native-design"
    cold = PipelineStudyEvaluator(None, {}, training_set=training)
    assert cold.restore_progress({"proposal_index": 0, "rng_state": None, "observations": []})
    assert cold.history.excluded_geometry_hashes == ("family-surface",)


def test_legacy_cma_mae_emitter_remains_unbounded(smoke_cfg, tmp_path, monkeypatch):
    import ribs.emitters
    from test_search_cma_me import knob_eval, qd_block, two_knob_cfg

    real_emitter = ribs.emitters.EvolutionStrategyEmitter
    bounds = []

    def capture(*args, **kwargs):
        bounds.append(kwargs["bounds"])
        return real_emitter(*args, **kwargs)

    monkeypatch.setattr(ribs.emitters, "EvolutionStrategyEmitter", capture)
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(maes={"learning_rate": 0.05, "j_threshold": 20.0}))
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg))
    cma_mod.search(cfg, tmp_path / "legacy", "screen", backend=SyntheticBackend(), budget=2,
                   lib_shas=LIBS)
    assert bounds == [None]
