"""WP 2.1 wiring, GUI half: the allow-listed launcher forwards the config-resolved ``finalist``
fidelity tier to ``search --mode`` exactly like the three original tiers, and still refuses a token
the CLI parser would reject."""
from __future__ import annotations

import pytest

from hornlab_search.gui import jobs as J


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    (root / "examples").mkdir()
    (root / "examples" / "c.yaml").write_text("name: c\n", encoding="utf-8")
    return root


def _jm(repo) -> J.JobManager:
    return J.JobManager(repo, repo / "runs")


def test_search_modes_are_exactly_the_cli_tiers():
    assert set(J.SEARCH_MODES) == {"screen", "verify", "final", "finalist"}


def test_finalist_is_forwarded_to_search_mode(repo):
    argv, gpu = _jm(repo).build_argv("search", {"config": "examples/c.yaml", "mode": "finalist"})
    assert gpu is True
    i = argv.index("--mode")
    assert argv[i + 1] == "finalist"


@pytest.mark.parametrize("mode", ["screen", "verify", "final"])
def test_old_tiers_are_forwarded_unchanged(repo, mode):
    argv, _ = _jm(repo).build_argv("search", {"config": "examples/c.yaml", "mode": mode})
    i = argv.index("--mode")
    assert argv[i + 1] == mode


def test_absent_mode_adds_no_flag(repo):
    argv, _ = _jm(repo).build_argv("search", {"config": "examples/c.yaml"})
    assert "--mode" not in argv


def test_an_invalid_mode_is_still_refused(repo):
    with pytest.raises(J.JobError, match="mode"):
        _jm(repo).build_argv("search", {"config": "examples/c.yaml", "mode": "finalists"})
