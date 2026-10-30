"""Home dashboard progressive paint.

``/api/leaders`` takes ~18 s on the real data set while status / campaigns / runs return in well
under a second. ``viewHome`` used to await all four together, so Home (the default route) sat on
the skeleton for ~18 s with three panels already available.

These are source pins on ``app.js`` (same reader-level style as test_gui_brief_authoring.py):
the first paint waits only on the fast trio, the leaderboard is fetched afterwards and patched
into its own container, and the three literals pinned elsewhere (nav poll + its 10 s interval +
the /api/runs summary source) are untouched.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"


def _src() -> str:
    return APPJS.read_text(encoding="utf-8")


def _view_home_body(src: str) -> str:
    return src.split("async function viewHome() {", 1)[1].split("// ── View 1: Status", 1)[0]


def _patch_body(src: str) -> str:
    return src.split(
        "async function patchHomeLeaders(ROOT, myEpoch) {", 1
    )[1].split("\nasync function viewHome()", 1)[0]


def test_home_first_paint_skips_the_slow_leaderboard():
    """The first Promise.all in viewHome contains status + campaigns + runs and NOT leaders."""
    src = _src()
    body = _view_home_body(src)

    assert "Promise.all([" in body
    first_batch = body.split("Promise.all([", 1)[1].split("]);", 1)[0]
    assert 'api("/api/status")' in first_batch
    assert 'api("/api/campaigns")' in first_batch
    assert 'api("/api/runs")' in first_batch
    # the slow call is not part of the first paint, and does not even appear in the view body
    assert 'api("/api/leaders")' not in first_batch
    assert 'api("/api/leaders")' not in body
    assert first_batch.count("api(") == 3

    # the first paint (ROOT.innerHTML = dashboard) happens before the late leaderboard is requested
    assert "ROOT.innerHTML = `<div class=\"stack\"" in body
    assert "// leaders arrive after first paint" in body
    assert "patchHomeLeaders(ROOT, myEpoch);" in body
    assert body.index("ROOT.innerHTML = `<div class=\"stack\"") < body.index(
        "patchHomeLeaders(ROOT, myEpoch);"
    )


def test_home_leaderboard_has_a_stable_container_and_a_late_patch():
    """A dedicated #home-leaders wrapper lets the second response repaint only that region."""
    src = _src()

    assert '<div id="home-leaders">${bestBriefHtml}</div>' in src
    assert "function homeLeadersHtml(leaders, pending = false)" in src
    # first paint shows the pending placeholder, never a false "no scored campaigns" claim
    assert "const bestBriefHtml = homeLeadersHtml([], true);" in src

    patch = _patch_body(src)
    assert 'api("/api/leaders")' in patch
    assert 'ROOT.querySelector("#home-leaders")' in patch
    # stale responses are dropped: newer render (epoch) or navigation (ROOT identity)
    assert "if (myEpoch !== _homeEpoch || ROOT !== currentRoot()) return;" in patch
    assert "let _homeEpoch = 0;" in src
    assert "const myEpoch = ++_homeEpoch;" in _view_home_body(src)
    # a leaders failure degrades to an inline muted line, never a page-replacing error banner
    assert "Leaderboard unavailable — " in patch
    assert "errBanner(" not in patch


def test_pinned_nav_poll_and_runs_fetch_literals_still_exist():
    """test_gui_brief_authoring.py pins these verbatim; the Home change must not disturb them."""
    src = _src()
    assert "async function pollNavOnce()" in src
    assert "setInterval(() => { if (!document.hidden) pollNavOnce(); }, 10000)" in src
    assert 'api("/api/runs")' in src
