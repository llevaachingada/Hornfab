"""v7 scalar study replay must match the production scorer and refuse missing inputs."""
import dataclasses
import numpy as np
import pytest
from conftest import REPO, make_fake_response
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.objective import replay
from hornlab_search.objective.scalar_v7 import objective_v7

CONFIG = REPO / 'examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7.yaml'


def record():
    brief = replay.brief_from_config(CONFIG)
    response = make_fake_response()
    metrics = compute_metrics(response, brief.target)
    j, terms = objective_v7(metrics, response, True, brief.target, brief.weights, brief.objective_params)
    arrays = replay._arrays_from_response(response)
    arrays.update({k: np.asarray(getattr(metrics, k)) for k in
                   ('bw_h_deg', 'bw_v_deg', 'di_db', 'ripple_h_db', 'ripple_v_db', 'on_axis_db')})
    meta = {'ok': True, 'design_hash': 'design', 'mesh_hash': 'mesh', 'solve_hash': 'solve',
            'objective_version': 7, 'objective': j, 'terms': terms,
            'metrics_scalars': metrics.scalars, 'target': dataclasses.asdict(brief.target)}
    return brief, meta, arrays, j


def test_v7_replay_matches_canonical_production_score():
    brief, meta, arrays, j = record()
    result = replay.replay_record(meta, arrays, brief=brief)
    assert result.status == replay.STATUS_EXACT_COMPLETE
    assert result.j == pytest.approx(j, abs=1e-9)
    assert result.parity_delta == pytest.approx(0, abs=1e-9)
    assert result.diagnostics['diag_available'] is True


def test_v7_replay_refuses_missing_impedance_and_balloon():
    brief, meta, arrays, _ = record()
    arrays.pop('z_throat')
    result = replay.replay_record(meta, arrays, brief=brief)
    assert result.j is None and replay.R_MISSING_IMPEDANCE in result.reasons
    brief, meta, arrays, _ = record()
    arrays.pop('balloon_dirs')
    arrays.pop('spl_balloon_db')
    result = replay.replay_record(meta, arrays, brief=brief)
    assert result.status != replay.STATUS_EXACT_COMPLETE
    assert replay.R_MISSING_BALLOON in result.reasons
