"""Offline tests for mesh/grid.py (the issue-#9 seam over build_point_grid)."""
from __future__ import annotations

import sys
import types

import pytest

from hornlab_search.mesh import grid


def _fake_mesher(monkeypatch, build=None):
    """Install fake ``hornlab_mesher`` / ``hornlab_mesher.config_builder`` modules so the lazy
    import inside grid.build_point_grid resolves to something we control."""
    fake_mesher = types.ModuleType("hornlab_mesher")
    fake_cb = types.ModuleType("hornlab_mesher.config_builder")
    if build is not None:
        setattr(fake_cb, "build_point_grid", build)
    monkeypatch.setitem(sys.modules, "hornlab_mesher", fake_mesher)
    monkeypatch.setitem(sys.modules, "hornlab_mesher.config_builder", fake_cb)
    return fake_cb


def test_build_point_grid_delegates_and_passes_keyword(monkeypatch):
    calls = {}

    def fake_build(params, *, defer_osse_offset_repair=False):
        calls["params"] = params
        calls["kw"] = defer_osse_offset_repair
        return {"inner_points": [1.0], "outer_points": None}

    _fake_mesher(monkeypatch, build=fake_build)
    out = grid.build_point_grid({"a": 1}, defer_osse_offset_repair=True)
    assert out == {"inner_points": [1.0], "outer_points": None}
    assert calls == {"params": {"a": 1}, "kw": True}


def test_build_point_grid_missing_mesher_raises_clear_error(monkeypatch):
    # a config_builder module present but WITHOUT build_point_grid makes the lazy import fail
    _fake_mesher(monkeypatch, build=None)
    with pytest.raises(RuntimeError, match="test_mesh_pin.py"):
        grid.build_point_grid({})
