"""Stage 0 WP 0.4 (2026-11-17): replay dispatches v9 and regenerates DI the production way."""
import inspect

from hornlab_search.objective import replay


def test_replay_accepts_and_dispatches_v9():
    src = inspect.getsource(replay)
    assert "if version not in (1, 2, 3, 4, 7, 9):" in src
    assert "objective_v9(metrics, response, True, target, weights, params)" in src


def test_v9_block_validated_by_v9params():
    import pytest
    with pytest.raises(ValueError):
        replay._params_from_block(9, None)


def test_regeneration_uses_production_metrics_not_plain_compute_metrics():
    src = inspect.getsource(replay._replay_core)
    assert "compute_metrics(" not in src
    assert src.count("_parity_metrics(response, requested_target)") == 2
    from hornlab_search.search.evaluate import metrics_from_response
    assert "metrics_from_response" in inspect.getsource(replay._parity_metrics)
    assert callable(metrics_from_response)
