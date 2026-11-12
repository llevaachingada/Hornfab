"""WP7 backend: ``jobs.build_argv("verify", ...)`` accepts explicit design hashes.

cli.py already exposes ``verify --top N | --designs h1,h2 | --designs-file f.csv`` as an argparse
mutually exclusive group (cli.py:1547-1550); ``_verify_wanted_hashes`` (cli.py:813) keeps the
caller's order and drops duplicates. These tests pin the GUI half to the same rules: validated
shape only (no filesystem probe for the hashes/CSV — the CLI owns that), ``--top`` unchanged for
backward compatibility, and no invented precedence when two selectors are supplied.
"""
from __future__ import annotations

import pytest

from hornlab_search.gui import jobs as J

RUN = "20261025T000001Z-screen-bbb222"
H1 = "aaaaaa"          # the loader's own hashes are lowercase hex, 6-40 chars (data.HASH)
H2 = "bbbbbb"
H3 = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "runs" / RUN).mkdir(parents=True)
    return root


def _jm(repo) -> J.JobManager:
    return J.JobManager(repo, repo / "runs")


def _run_path(repo) -> str:
    return str((repo / "runs").resolve() / RUN)


# ------------------------------------------------------------------ backward compatibility


def test_verify_run_plus_top_is_unchanged(repo):
    argv, gpu = _jm(repo).build_argv("verify", {"run": RUN, "top": 12})
    assert gpu is True                       # verify stays a GPU job (one-GPU lock via launch)
    assert argv == ["verify", "--run", _run_path(repo), "--top", "12"]


def test_verify_top_defaults_to_five_when_omitted(repo):
    argv, gpu = _jm(repo).build_argv("verify", {"run": RUN})
    assert gpu is True
    assert argv == ["verify", "--run", _run_path(repo), "--top", "5"]


# ------------------------------------------------------------------ designs (string / list)


def test_verify_designs_string_argv(repo):
    argv, gpu = _jm(repo).build_argv("verify", {"run": RUN, "designs": f"{H1},{H2}"})
    assert gpu is True
    assert argv == ["verify", "--run", _run_path(repo), "--designs", f"{H1},{H2}"]


def test_verify_designs_list_keeps_order_and_drops_duplicates(repo):
    argv, gpu = _jm(repo).build_argv(
        "verify", {"run": RUN, "designs": [f" {H2} ", H1, H2, "", H3]})
    assert gpu is True
    assert argv == ["verify", "--run", _run_path(repo), "--designs", f"{H2},{H1},{H3}"]


def test_verify_designs_takes_any_valid_hex_length(repo):
    low, high = "abcdef", "f" * 40
    argv, _ = _jm(repo).build_argv("verify", {"run": RUN, "designs": [low, high]})
    assert argv[-1] == f"{low},{high}"


def test_verify_designs_keeps_brief_last(repo):
    brief = repo / "examples"
    brief.mkdir(parents=True)
    (brief / "b.yaml").write_text("name: b\n", encoding="utf-8")
    argv, _ = _jm(repo).build_argv(
        "verify", {"run": RUN, "designs": H1, "brief": "examples/b.yaml"})
    assert argv == ["verify", "--run", _run_path(repo), "--designs", H1,
                    "--brief", "examples/b.yaml"]


# ------------------------------------------------------------------ designs_file


def test_verify_designs_file_argv(repo):
    argv, gpu = _jm(repo).build_argv("verify", {"run": RUN, "designs_file": " picks.csv "})
    assert gpu is True
    assert argv == ["verify", "--run", _run_path(repo), "--designs-file", "picks.csv"]


def test_verify_designs_file_does_not_probe_the_filesystem(repo):
    # The CLI opens the CSV; build_argv only validates the shape of the argument.
    argv, _ = _jm(repo).build_argv("verify", {"run": RUN, "designs_file": "does/not/exist.csv"})
    assert argv[-2:] == ["--designs-file", "does/not/exist.csv"]


# ------------------------------------------------------------------ refusals


@pytest.mark.parametrize("designs", [[], ["", "   "], "  ,  ",
                                     ["not-hex"], ["ABCDEF"], ["abcde"], ["a" * 41],
                                     [5], [None], True, 7])
def test_verify_designs_rejects_empty_or_malformed_hashes(repo, designs):
    with pytest.raises(J.JobError, match="designs"):
        _jm(repo).build_argv("verify", {"run": RUN, "designs": designs})


def test_verify_designs_file_rejects_empty_path(repo):
    with pytest.raises(J.JobError, match="designs_file"):
        _jm(repo).build_argv("verify", {"run": RUN, "designs_file": "   "})


@pytest.mark.parametrize("args", [
    {"designs": H1, "designs_file": "picks.csv"},
    {"designs": H1, "top": 5},
    {"designs_file": "picks.csv", "top": 5},
])
def test_verify_selectors_are_mutually_exclusive_like_the_cli(repo, args):
    # cli.py's argparse group refuses --top with --designs/--designs-file and the two hash
    # selectors together; the GUI mirrors that refusal instead of inventing a precedence.
    with pytest.raises(J.JobError):
        _jm(repo).build_argv("verify", {"run": RUN, **args})


def test_verify_designs_still_needs_a_known_run(repo):
    with pytest.raises(J.JobError, match="unknown run"):
        _jm(repo).build_argv("verify", {"run": "not-a-run", "designs": H1})
