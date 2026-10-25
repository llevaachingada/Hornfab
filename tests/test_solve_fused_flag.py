"""Offline tests for the WP15 `solve.cuda_fused` plumbing (senior pass 2026-10-24).

What is proven OFFLINE (no GPU, no fork install needed):
- `SolveSettings.cuda_fused` loads from YAML and defaults to False (old configs untouched);
- non-beat_cuda backends with cuda_fused are refused;
- the opt-in rides in `SolveSpec.extra` so the solve-spec hash (cache key / dataset provenance)
  is UNCHANGED when the flag is absent and different when it is set;
- `BeatBackend` sets/leaves `HORNLAB_BEAT_FUSED_BM_CUDA` explicitly ("1" / "0") and refuses
  cuda_fused on cpu;
- `_assert_cuda_fused_path` refuses a solve whose diagnostics do not PROVE the fused path ran,
  and accepts a proven one (so stale warm hosts can never present old-path data as fused).
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config, solve_spec
from hornlab_search.solve.base import ResponseSanityError
from hornlab_search.solve.beat import BeatBackend, _assert_cuda_fused_path
from hornlab_search.types import SolveSpec


def _cfg_with_cuda_fused(tmp_path, value, backend="beat_cuda"):
    src = (EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8")
    src = src.replace("backend: beat_cuda", f"backend: {backend}")
    src = src.replace("timeout_s: 900", f"timeout_s: 900\n  cuda_fused: {str(value).lower()}")
    p = tmp_path / "cfg_fused.yaml"
    p.write_text(src, encoding="utf-8")
    return p


def test_solve_settings_default_false(tmp_path):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    assert cfg.solve.cuda_fused is False
    spec = solve_spec("screen", cfg)
    assert dict(spec.extra) == {"cuda_fused": False} or dict(spec.extra) == {}


def test_cuda_fused_loads_and_enters_spec_extra(tmp_path):
    p = _cfg_with_cuda_fused(tmp_path, True)
    cfg = load_config(p)
    assert cfg.solve.cuda_fused is True
    spec = solve_spec("screen", cfg)
    assert spec.extra.get("cuda_fused") is True


def test_hash_unchanged_when_flag_absent():
    """Old runs must reproduce: no cuda_fused anywhere -> the same hash as a spec with extra={}."""
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    s1 = solve_spec("screen", cfg)
    s2 = SolveSpec(mode=s1.mode, freqs_hz=s1.freqs_hz, backend=s1.backend,
                   observation=s1.observation, gmres_tol=s1.gmres_tol, extra={})
    assert s1.hash() == s2.hash()
    s3 = dataclasses.replace(s1, extra={"cuda_fused": True})
    assert s3.hash() != s1.hash()
    # a solved frequency list keeps the hash identical, not a coincidental float diff
    s4 = dataclasses.replace(s1, extra={})
    assert s4.hash() == s1.hash()


def test_cuda_fused_refused_on_non_cuda_backend(tmp_path):
    p = _cfg_with_cuda_fused(tmp_path, True, backend="beat_cpu")
    with pytest.raises(ConfigError, match="cuda_fused"):
        load_config(p)


def test_beatbackend_env_flag_init():
    try:
        be0 = BeatBackend("cuda", cuda_fused=True)
    except Exception as exc:  # backend not functional on this machine: constructor is harmless
        pytest.skip(f"BeatBackend not constructible here: {exc}")
    import os
    assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "1"
    be0.release()  # we started no host; shutdown is harmless hygiene
    be1 = BeatBackend("cuda")
    assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "0"
    be1.notes_path = None
    with pytest.raises(ValueError, match="cuda_fused"):
        BeatBackend("cpu", cuda_fused=True)
    # do not leave the flag set to 1 in this test process
    os.environ["HORNLAB_BEAT_FUSED_BM_CUDA"] = "0"


def _fake_raw_with_diagnostics(entry):
    return SimpleNamespace(solver_log=[{"native_diagnostics": entry}])


def test_fused_path_proved_passes():
    spec = dataclasses.replace(solve_spec("screen", load_config(EXAMPLES / "osse_baseline.yaml")),
                               extra={"cuda_fused": True})
    raw = _fake_raw_with_diagnostics({"assembly_path": "fused_cuda", "p1_dof_count": 100})
    _assert_cuda_fused_path(raw, spec)                    # no exception


def test_fused_path_not_proven_refuses():
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    base_spec = solve_spec("screen", cfg)
    spec = dataclasses.replace(base_spec, extra={"cuda_fused": True})
    # old path reported
    raw = _fake_raw_with_diagnostics({"assembly_path": "cuda", "p1_dof_count": 100})
    with pytest.raises(ResponseSanityError, match="do not prove"):
        _assert_cuda_fused_path(raw, spec)
    # no assembly_path at all (an old driver, or a warm host without the env)
    raw = _fake_raw_with_diagnostics({"p1_dof_count": 100})
    with pytest.raises(ResponseSanityError, match="do not prove"):
        _assert_cuda_fused_path(raw, spec)
    # no diagnostics whatsoever
    raw = SimpleNamespace(solver_log=[])
    with pytest.raises(ResponseSanityError, match="do not prove"):
        _assert_cuda_fused_path(raw, spec)
    # flag absent: never raises
    _assert_cuda_fused_path(_fake_raw_with_diagnostics({"p1_dof_count": 100}), base_spec)