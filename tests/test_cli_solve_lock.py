"""Two-lane rule: a CPU-backend command never takes the GPU lock (2026-11-12 day-queue bug)."""
from __future__ import annotations

import contextlib
from types import SimpleNamespace

from hornlab_search import cli


def _is_null(ctx) -> bool:
    return isinstance(ctx, contextlib.nullcontext)


def test_cpu_backend_skips_gpu_lock(tmp_path, monkeypatch):
    monkeypatch.delenv("HORNLAB_BEAT_WORKER_DIR", raising=False)
    for b in ("beat_cpu", "bempp_cpu"):
        assert _is_null(cli._solve_lock("x", SimpleNamespace(backend=b), tmp_path))


def test_cpu_lane_env_skips_gpu_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", str(tmp_path / "runs" / "lanes" / "cpu" / "workers"))
    assert _is_null(cli._solve_lock("x", SimpleNamespace(backend=None), tmp_path))


def test_gpu_and_default_take_gpu_lock(tmp_path, monkeypatch):
    monkeypatch.delenv("HORNLAB_BEAT_WORKER_DIR", raising=False)
    for b in (None, "beat_cuda"):
        assert not _is_null(cli._solve_lock("x", SimpleNamespace(backend=b), tmp_path))
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", str(tmp_path / "runs" / "lanes" / "gpu" / "workers"))
    assert not _is_null(cli._solve_lock("x", SimpleNamespace(backend=None), tmp_path))


def test_gpu_clean_accepts_lane():
    p = cli.build_parser() if hasattr(cli, "build_parser") else None
    if p is None:
        return
    a = p.parse_args(["gpu-clean", "--lane", "gpu"])
    assert a.lane == "gpu"
