"""WP5: ``solve.source_motion`` reaches the beat SolveConfig; 'normal' never enters the hash.

Offline: a stand-in ``hornlab_beat_bem`` module records the SolveConfig kwargs, so no solver, GPU or
persistent Julia host is involved.
"""
from __future__ import annotations

import dataclasses
import sys

from conftest import EXAMPLES
from hornlab_search.config import load_config, solve_spec
from hornlab_search.solve.beat import BeatBackend
from hornlab_search.types import MeshResult


class _FakeBeat:
    class ObservationConfig:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class ObservationFrame:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class SolveConfig:
        def __init__(self, **kw):
            self.__dict__.update(kw)


def _mesh() -> MeshResult:
    return MeshResult(path="", n_triangles=1, n_dof=None, quadrants="1",
                      symmetry_plane="yz+xz", res_mm={}, bbox_m=(0.0, 0.0, 0.0, 0.1, 0.1, 0.1),
                      seconds=0.0)


def test_beat_solve_config_always_receives_source_motion(monkeypatch, cfg):
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", _FakeBeat)
    be = BeatBackend("cuda")
    spec = solve_spec("screen", cfg)
    assert be.make_config(_mesh(), spec).source_motion == "normal"

    axial = dataclasses.replace(spec, extra={**spec.extra, "source_motion": "axial"})
    assert be.make_config(_mesh(), axial).source_motion == "axial"


def test_source_motion_is_absent_from_extra_until_it_differs():
    cfg = load_config(EXAMPLES / "search_smoke.yaml")
    assert cfg.solve.source_motion == "normal"
    assert solve_spec("screen", cfg).extra == {}
