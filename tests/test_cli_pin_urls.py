"""The pyproject pin parser accepts upstream, GitHub-fork and local file:// fork URLs (docs/FORKS.md)."""
from hornlab_search import cli

SHA = "38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0"


def _parse(line: str):
    m = cli._GIT_URL_RE.search(line)
    return None if m is None else (m.group(1), m.group(2))


def test_upstream_url_parses_as_before():
    line = f'  "hornlab-beat-bem @ git+https://github.com/m3gnus/hornlab-beat-bem.git@{SHA}",'
    assert _parse(line) == ("hornlab-beat-bem", SHA)


def test_github_fork_url_parses():
    line = f'  "hornlab-beat-bem @ git+https://github.com/someone/hornlab-beat-bem.git@{SHA}",'
    assert _parse(line) == ("hornlab-beat-bem", SHA)


def test_local_file_fork_url_parses():
    line = f'  "hornlab-waveguide-mesher @ git+file:///C:/Users/x/Hrns/forks/hornlab-waveguide-mesher@{SHA}",'
    assert _parse(line) == ("hornlab-waveguide-mesher", SHA)


def test_optional_dependency_line_parses():
    line = f'crosscheck = ["hornlab-bempp-bem @ git+https://github.com/m3gnus/hornlab-bempp-bem.git@{SHA}"]'
    assert _parse(line) == ("hornlab-bempp-bem", SHA)


def test_short_or_missing_sha_is_not_a_pin():
    assert _parse('"hornlab-beat-bem @ git+https://github.com/m3gnus/hornlab-beat-bem.git@main",') is None
    assert _parse('"hornlab-beat-bem>=0.2"') is None


def test_shipped_pyproject_still_yields_every_pin():
    pins = cli._expected_shas()
    assert {"hornlab-waveguide-mesher", "hornlab-beat-bem", "hornlab-plots"} <= set(pins)
    assert all(len(s) == 40 for s in pins.values())
