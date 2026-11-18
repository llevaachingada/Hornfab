"""WP 0.4 hardening (R17, cloud senior 2026-11-18): the replay gate and the replay dispatch use one
version list. The v10 gap (dispatch existed, gate refused) cannot recur silently."""
import inspect

from hornlab_search.objective import replay
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS


def test_every_admitted_version_has_a_dispatch_branch():
    src = inspect.getsource(replay._dispatch)
    for v in replay.REPLAY_VERSIONS:
        assert f"if version == {v}:" in src, v


def test_admitted_versions_are_supported_and_exclusions_are_named():
    assert set(replay.REPLAY_VERSIONS) <= set(SUPPORTED_OBJECTIVE_VERSIONS)
    not_replayable = set(SUPPORTED_OBJECTIVE_VERSIONS) - set(replay.REPLAY_VERSIONS)
    # A new supported version must be either replayable or added here on purpose.
    assert not_replayable == {5, 6}


def test_gate_reads_the_single_list():
    assert "if version not in REPLAY_VERSIONS:" in inspect.getsource(replay._replay_core)
