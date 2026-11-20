"""WP3.4 — the GUI-written finding state store (gui/data_overview_state.py).

Headless and offline: a synthetic ``runs/`` directory. No solver, no GPU.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hornlab_search.gui import data_overview_state as S

FID = "0123456789abcdef"


def _runs(tmp_path: Path) -> Path:
    return tmp_path / "runs"


# ---------------------------------------------------------------------------- persistence

def test_dismiss_survives_reload(tmp_path):
    runs = _runs(tmp_path)
    S.set_status(runs, FID, "dismissed", note="known tie, verified later")

    on_disk = S.state_path(runs)
    assert on_disk.is_file()
    assert on_disk.parent.name == "overview"

    reloaded = S.load_state(runs)
    assert reloaded[FID]["status"] == "dismissed"
    assert reloaded[FID]["note"] == "known tie, verified later"
    assert reloaded[FID]["by"] == "gui"
    assert reloaded[FID]["at_utc"].endswith("Z")


def test_open_reopens_a_dismissed_finding(tmp_path):
    runs = _runs(tmp_path)
    S.set_status(runs, FID, "dismissed")
    S.set_status(runs, FID, "open")
    assert S.load_state(runs)[FID]["status"] == "open"


def test_load_state_missing_file_is_empty(tmp_path):
    assert S.load_state(_runs(tmp_path)) == {}


def test_load_state_corrupt_file_is_empty_without_raising(tmp_path):
    runs = _runs(tmp_path)
    path = S.state_path(runs)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert S.load_state(runs) == {}
    # A write after a corrupt file repairs it rather than crashing.
    state = S.set_status(runs, FID, "acknowledged")
    assert state[FID]["status"] == "acknowledged"


# ---------------------------------------------------------------------------- validation

@pytest.mark.parametrize("status", ["hidden", "RESOLVED", "", None])
def test_bad_status_raises_value_error(tmp_path, status):
    with pytest.raises(ValueError):
        S.set_status(_runs(tmp_path), FID, status)


@pytest.mark.parametrize("fid", ["", "abc", "z" * 16, FID + "0", "0123456789ABCDEF", None, 16])
def test_bad_finding_id_raises_value_error(tmp_path, fid):
    with pytest.raises(ValueError):
        S.set_status(_runs(tmp_path), fid, "dismissed")


# ---------------------------------------------------------------------------- atomic write

def test_atomic_write_leaves_no_tmp_behind(tmp_path):
    runs = _runs(tmp_path)
    S.set_status(runs, FID, "dismissed")
    files = [p.name for p in S.state_path(runs).parent.iterdir()]
    assert files == ["finding_state.json"]
    assert not any(name.endswith(".tmp") for name in files)


# ---------------------------------------------------------------------------- merge rule

def _finding(status: str, fid: str = FID) -> dict:
    return {"id": fid, "kind": "budget", "severity": "high", "status": status}


def test_resolved_finding_stays_resolved_after_merge():
    state = {FID: {"status": "dismissed", "note": None, "by": "gui", "at_utc": "2026-11-19T00:00:00Z"}}
    out = S.merge_state([_finding("resolved")], state)
    assert out[0]["status"] == "resolved"


def test_state_wins_over_a_computed_open():
    state = {FID: {"status": "acknowledged", "note": "seen", "by": "gui", "at_utc": "x"}}
    out = S.merge_state([_finding("open")], state)
    assert out[0]["status"] == "acknowledged"
    assert out[0]["state_note"] == "seen"


def test_state_wins_over_a_computed_superseded():
    state = {FID: {"status": "dismissed", "note": None, "by": "gui", "at_utc": "x"}}
    out = S.merge_state([_finding("superseded")], state)
    assert out[0]["status"] == "dismissed"


def test_merge_does_not_mutate_the_input_and_empty_state_is_a_noop():
    finding = _finding("open")
    assert S.merge_state([finding], {})[0] is finding
    state = {FID: {"status": "dismissed"}}
    S.merge_state([finding], state)
    assert finding["status"] == "open"


def test_merge_ignores_unknown_state_status():
    state = {FID: {"status": "bogus"}}
    assert S.merge_state([_finding("open")], state)[0]["status"] == "open"


def test_end_to_end_dismiss_then_merge(tmp_path):
    runs = _runs(tmp_path)
    S.set_status(runs, FID, "dismissed")
    state = S.load_state(runs)
    out = S.merge_state([_finding("open", FID), _finding("resolved", "fedcba9876543210")], state)
    assert out[0]["status"] == "dismissed"
    assert out[1]["status"] == "resolved"
