"""Guard: installed HornLab packages must match the pyproject.toml pins.

Issue #9 resolution (senior ruling 2026-10-13): `hornlab_mesher.config_builder.
build_point_grid` stays private API by decision; the protection the project
relies on is that a silent mesher bump fails loudly here instead of silently
invalidating meshes, cache keys, resumed searches and every dataset row.

Notes on the environment:
- A mismatch between the installed commit and the pin is a hard failure.
- An UNKNOWN commit ("" from direct_url.json) is permitted, because CI installs
  the heavy HornLab packages as importable-but-inert stubs that carry no git
  metadata. On a real dev install (this machine) every pin is checked exactly.
"""
import pytest

from hornlab_search import cli


def test_installed_hornlab_packages_match_their_pins():
    expected = cli._expected_shas()
    assert expected, "no pinned git dependencies found in pyproject.toml"
    installed = cli._installed_shas()
    mismatches, unknown = [], []
    for repo, want in sorted(expected.items()):
        got = installed.get(repo, "")
        if not got:
            unknown.append(repo)
        elif got != want:
            mismatches.append(f"{repo}: installed {got[:12]} != pinned {want[:12]}")
    assert not mismatches, (
        "Silent HornLab version bump detected (invalidates meshes, cache keys, "
        "dataset rows and resumed searches): "
        + "; ".join(mismatches)
        + " - either restore the pinned commit, or consciously bump pyproject.toml "
        "+ TOOLCHAIN.md and re-run every package-gated test before trusting results."
    )
    # unknown repos are reported, not asserted: CI genuinely cannot resolve them.
    if unknown:
        print(f"NOTE: git SHA unknown for (stubs/CI): {', '.join(sorted(unknown))}")