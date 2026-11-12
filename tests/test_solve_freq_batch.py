"""WP5 (throughput packet): the opt-in ``freq_batch_size`` knob. Offline, fake solver module."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.solve.beat import BeatBackend, frequency_groups
from hornlab_search.types import MeshResult, SolveSpec, ObservationSpec

F12 = [500.0 * 1.2 ** i for i in range(12)]


def test_default_grouping_is_unchanged():
    assert frequency_groups(F12, True, None) == [[f] for f in F12]      # CUDA / Metal today
    assert frequency_groups(F12, False, None) == [F12]                  # CPU today


@pytest.mark.parametrize("n,expected_calls", [(1, 12), (2, 6), (4, 3), (5, 3), (12, 1), (50, 1)])
def test_batches_keep_every_frequency_in_order(n, expected_calls):
    groups = frequency_groups(F12, True, n)
    assert len(groups) == expected_calls
    assert [f for g in groups for f in g] == F12
    assert all(1 <= len(g) <= n for g in groups)


def test_bad_batch_size_is_refused(monkeypatch):
    with pytest.raises(ValueError):
        frequency_groups(F12, True, 0)
    with pytest.raises(ValueError):
        BeatBackend("cpu", freq_batch_size=0)


def test_env_knob_and_default(monkeypatch):
    monkeypatch.delenv("HORNLAB_FREQ_BATCH_SIZE", raising=False)
    assert BeatBackend("cpu").freq_batch_size is None
    monkeypatch.setenv("HORNLAB_FREQ_BATCH_SIZE", "4")
    assert BeatBackend("cpu").freq_batch_size == 4
    assert BeatBackend("cpu", freq_batch_size=2).freq_batch_size == 2   # explicit arg wins


def _fake_beat(calls):
    def solve_frequencies(path, freqs, cfg):
        calls.append(list(freqs))
        n = len(freqs)
        return SimpleNamespace(
            observation_angles_deg=np.linspace(-90, 90, 3), observation_planes=["h", "v"],
            timings={"t": 1.0}, solver_log=[{} for _ in freqs],
            frequencies_hz=np.asarray(freqs, dtype=float), config=None, mesh_info=None,
            requested_frequency_count=n, channel_tags=None, tag_areas_m2=None)
    return SimpleNamespace(solve_frequencies=solve_frequencies)


def test_solve_raw_sends_the_configured_groups(monkeypatch):
    calls: list = []
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", _fake_beat(calls))
    mesh = MeshResult(path="m.msh", n_triangles=1, n_dof=None, quadrants="1", symmetry_plane="yz+xz",
                      res_mm={}, bbox_m=(0,) * 6, seconds=0.0)
    spec = SolveSpec(mode="screen", freqs_hz=tuple(F12), backend="beat_cuda",
                     observation=ObservationSpec(0.5, 3, False, 0), gmres_tol=1e-4, extra={})
    for n, expected in ((None, 12), (4, 3), (12, 1)):
        calls.clear()
        be = BeatBackend("cuda", freq_batch_size=n, track_vram=False)
        raw = be.solve_raw(mesh, spec, cfg=object())
        assert len(calls) == expected
        assert [f for c in calls for f in c] == F12
        assert list(raw.frequencies_hz) == F12              # nothing dropped, nothing reordered
