"""A2: the band-split seam probe is the lower band's LAST frequency, solved on the UPPER mesh."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hornlab_search.config import mode_freqs
from hornlab_search.design.space import DesignSpace
from hornlab_search.search.evaluate import (SEAM_MAX_AXIS_DB, evaluate, make_context,
                                            split_freq_bands)
from hornlab_search.types import SolveOutcome
from test_search_evaluate import _BandRecorder, _install_recording
from test_search_support import LIBS, fast_cfg

EDGE = 3000.0


class _MeshRecorder(_BandRecorder):
    def __init__(self, bump_db: float = 0.0):
        super().__init__()
        self.calls_log = []          # (mesh path, freqs)
        self.bump_db = bump_db

    def _solve(self, mesh, spec):
        self.calls_log.append((str(mesh.path), tuple(spec.freqs_hz)))
        out = super()._solve(mesh, spec)
        # a seam probe is a single-frequency solve on the upper (band1) mesh
        if self.bump_db and len(spec.freqs_hz) == 1 and "band1" in str(mesh.path):
            r = out.response
            r.spl_h_db = np.asarray(r.spl_h_db, dtype=float) + self.bump_db
            r.spl_v_db = np.asarray(r.spl_v_db, dtype=float) + self.bump_db
            return SolveOutcome(True, r, out.seconds, out.peak_vram_mb, "")
        return out


def _run(monkeypatch, smoke_cfg, tmp_path, backend):
    base = fast_cfg(smoke_cfg)
    cfg = dataclasses.replace(
        base, mesh=dataclasses.replace(base.mesh, band_split={"edges_hz": [EDGE]}))
    space = DesignSpace.from_config(base)
    _install_recording(monkeypatch, backend, [])
    ctx = make_context(cfg, None, lib_shas=LIBS)
    ev = evaluate(space.seed, space, cfg, "verify", tmp_path / "v", None, backend, ctx=ctx)
    assert not ev.error
    from hornlab_search.solve.cache import load_response
    resp = load_response(tmp_path / "v" / "designs" / ev.design_hash / "response.npz")
    return cfg, resp


def test_probe_frequency_is_within_the_lower_band(monkeypatch, smoke_cfg, tmp_path):
    cfg, resp = _run(monkeypatch, smoke_cfg, tmp_path, _MeshRecorder())
    lower = split_freq_bands(mode_freqs("verify", cfg), [EDGE])[0]
    seam = resp.meta["seam_check"]["3000"]
    assert seam["freq_hz"] <= max(lower)
    assert seam["freq_hz"] == max(lower)
    assert seam["pass"] is True
    assert resp.meta["seam_ok"] is True
    assert len(resp.meta["band_meshes"]) == 2


def test_probe_is_solved_on_the_upper_mesh(monkeypatch, smoke_cfg, tmp_path):
    backend = _MeshRecorder()
    cfg, resp = _run(monkeypatch, smoke_cfg, tmp_path, backend)
    f = resp.meta["seam_check"]["3000"]["freq_hz"]
    probes = [(p, fr) for p, fr in backend.calls_log if fr == (f,)]
    assert len(probes) == 1
    assert "band1" in probes[0][0].replace("\\", "/")


def test_large_delta_fails_the_seam_without_failing_the_candidate(monkeypatch, smoke_cfg, tmp_path):
    cfg, resp = _run(monkeypatch, smoke_cfg, tmp_path, _MeshRecorder(bump_db=5.0))
    seam = resp.meta["seam_check"]["3000"]
    assert abs(seam["on_axis_delta_db"]) > SEAM_MAX_AXIS_DB
    assert seam["pass"] is False
    assert resp.meta["seam_ok"] is False
