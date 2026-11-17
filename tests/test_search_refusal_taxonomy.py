"""Stage 0 WP 0.1 (2026-11-17): envelope refusals are coded as invalid_envelope, not geometry."""
import inspect

from hornlab_search.search import evaluate as ev


def test_plain_and_prefixed_envelope_generator_errors_map_to_envelope():
    for text in ("invalid_envelope: estimated outside",
                 "GeneratorError: invalid_envelope: mouth 612 mm > 600 mm",
                 "generator: GeneratorError: invalid_envelope: x"):
        assert ev._generator_error_kind(text) == ev.KIND_INVALID_ENV


def test_other_generator_errors_stay_geometry():
    for text in ("GeneratorError: self-approach 1.2 mm", "rows/symmetry mismatch", "",
                 "GeneratorError: not invalid_envelope"):
        assert ev._generator_error_kind(text) == ev.KIND_INVALID


def test_post_mesh_envelope_sites_are_envelope_kind():
    src = inspect.getsource(ev)
    assert 'KIND_INVALID, why, True' not in src
    assert src.count('KIND_INVALID_ENV, f"post_mesh: {why}", True') == 3


def test_graded_penalty_unchanged_without_overshoot():
    class _S:  # config with graded penalty but a design carrying no overshoot value
        infeasible_penalty = "graded"

    class _C:
        search = _S()

    class _D:
        params: dict = {}

    flat = ev._failure_penalty(ev.KIND_INVALID, _D(), _C())
    assert ev._failure_penalty(ev.KIND_INVALID_ENV, _D(), _C()) == flat
