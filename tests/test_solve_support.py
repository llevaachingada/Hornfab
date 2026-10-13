"""Shared helpers for the solver-gated solve tests (not tests themselves).

``tests/conftest.py`` is owned by task 03 and must not be edited, so the pieces the slow
tests share live here: build a real mesh from the seed design, print measured numbers LIVE
(``capsys.disabled``) so they appear in ``-v`` output without ``-s``, and the hygiene steps
around the persistent Julia host (AGENTS.md "GPU / Julia hygiene").
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np

from conftest import EXAMPLES
from hornlab_search.config import load_config, solve_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build
from hornlab_search.solve import worker
from hornlab_search.types import MeshResult, MeshSpec, SolveSpec


def emit(capsys, text: str) -> None:
    """Print ``text`` to the real terminal even for a passing test under ``-v``."""
    with capsys.disabled():
        print("\n  [measured] " + text.replace("\n", "\n  [measured] "), flush=True)


def seed_cfg():
    return load_config(EXAMPLES / "osse_baseline.yaml")


def seed_design(cfg=None):
    return DesignSpace.from_config(cfg or seed_cfg()).seed


def build_seed_mesh(out_dir: Path, quadrants: str, f_max_hz: float, *, epw: float = 6.0,
                    mode: str = "verify") -> MeshResult:
    """Mesh the seed design with the real mesher. ``mode='verify'`` (7,000-dof cap) so the 8 mm
    full-domain mesh (about 5.5k dofs) is allowed; the screen cap is 5,000."""
    cfg = seed_cfg()
    ms = MeshSpec(epw=epw, f_max_hz=float(f_max_hz), quadrants=quadrants, max_triangles=10**6)
    return build.build_mesh(seed_design(cfg), ms, cfg, Path(out_dir), mode=mode)


def spec_with(freqs, *, balloon: bool = True, mode: str = "screen") -> SolveSpec:
    spec = solve_spec(mode, seed_cfg())
    obs = spec.observation
    if not balloon:
        obs = dataclasses.replace(obs, balloon=False, balloon_points=0)
    return dataclasses.replace(spec, freqs_hz=tuple(float(f) for f in freqs), observation=obs)


def normalized_db(spl: np.ndarray, axis_index: int) -> np.ndarray:
    return spl - spl[:, axis_index:axis_index + 1]


def clean_host_state() -> dict:
    """Kill every BEAT host (verified) so a test starts from a clean state; return the VRAM
    baseline (MiB) read afterwards."""
    forced = worker.shutdown(verify=True)
    return {"killed_roots": forced, "vram_baseline_mib": worker.vram_used_mib(),
            "hosts_left": [h.pid for h in worker.list_beat_hosts()]}


def release_and_verify() -> dict:
    forced = worker.shutdown(verify=True)
    left = [h.pid for h in worker.list_beat_hosts()]
    return {"force_killed_roots": forced, "hosts_left": left, "vram_after_mib": worker.vram_used_mib()}
