"""Synthetic Evaluations for the dataset tests. No tests in here; the name keeps it next to them.

Imports only types, targets.spec (a frozen dataclass) and the conftest helpers: no solver, no mesher.
"""
from __future__ import annotations

import numpy as np

from conftest import FAKE_FREQS, make_fake_response
from hornlab_search.targets.spec import Target
from hornlab_search.types import (Design, Evaluation, MeshResult, MetricSet, ObservationSpec,
                                  SolveOutcome, SolveSpec)

LIB_SHAS = {
    "hornlab_mesher": "b922e807a5cf10cf732c4557ec0b9b495762afd7",
    "hornlab_beat_bem": "38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0",
    "hornlab_bempp_bem": "8e6910602ece9abb2e9ce0db7a637f4bedf17f53",
    "hornlab_plots": "9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44",
    "hornlab_search": "0123456789abcdef0123456789abcdef01234567",
}
LIB_SHAS_B = dict(LIB_SHAS, hornlab_beat_bem="ffffffffffffffffffffffffffffffffffffffff")

TARGET = Target(coverage_h_deg=90.0, coverage_v_deg=60.0, band_lo_hz=700.0, band_hi_hz=10000.0,
                di_target_db=None, freq_weights={1000.0: 2.0, 4000.0: 1.0})

GRID = {"angular_segments": 64, "length_segments": 32, "available": True}


def solve_spec(freqs=FAKE_FREQS, mode="screen") -> SolveSpec:
    return SolveSpec(mode=mode, freqs_hz=tuple(freqs), backend="beat_cuda",
                     observation=ObservationSpec(distance_m=2.0, angle_count=73, balloon=True,
                                                 balloon_points=512),
                     gmres_tol=1e-5)


def params_for(family: str, i: int) -> dict:
    t = (i % 97) / 97.0
    if family == "OSSE":
        return {"r0_mm": 12.7 + 3.0 * t, "a_deg": 40.0 + 10.0 * t, "L_mm": 120.0 + 40.0 * t,
                "k": 0.5 + t, "n": 4.0, "s": 0.7 + 0.1 * t}
    if family == "R-OSSE":
        return {"R_mm": 90.0 + 20.0 * t, "tmax": 0.9, "m": 0.8 + 0.1 * t, "r": 0.4, "b": 0.3}
    if family == "ICW":
        return {"termination": "flat_baffle", "r0_mm": 12.7, "L_mm": 100.0 + 30.0 * t,
                "coverage_angle_deg": 90.0}
    return {"profileH": [[0.0, 12.7], [100.0, 80.0 + t]], "throatAngleDeg": 10.0 + t,
            "inflectionPolicy": "none"}


def make_eval(i: int = 0, family: str = "OSSE", ok: bool = True, *, nf: int | None = None,
              error: str = "boom", seed: int = 0, objective: float | None = None) -> Evaluation:
    """A complete Evaluation (ok) or a failure (ok=False: no outcome, no metrics, no mesh)."""
    design = Design(family=family, params=params_for(family, i))
    dh = f"{i:012x}"
    if not ok:
        return Evaluation(design_hash=dh, design=design, mesh_hash="m" + dh[1:], solve_hash="s" + dh[1:],
                          objective=1e3, terms={"total": 1e3, "penalty": 1e3}, metrics=None,
                          mesh=None, outcome=None, error=error)
    resp = make_fake_response()
    if nf is not None:
        resp.freqs_hz = resp.freqs_hz[:nf].copy()
        resp.spl_h_db = resp.spl_h_db[:nf].copy()
        resp.spl_v_db = resp.spl_v_db[:nf].copy()
        resp.spl_balloon_db = resp.spl_balloon_db[:nf].copy()
        resp.z_throat = resp.z_throat[:nf].copy()
    rng = np.random.default_rng(seed + i)
    # Make every record's arrays distinct so a round-trip test cannot pass by accident.
    resp.spl_h_db = resp.spl_h_db + rng.normal(0.0, 0.01, resp.spl_h_db.shape)
    n = resp.freqs_hz.size
    ripple = rng.uniform(0.2, 2.0, n)
    ripple[0] = np.nan                       # NaN is legitimate here (<5 samples) and must survive
    ms = MetricSet(
        freqs_hz=resp.freqs_hz.copy(),
        bw_h_deg=rng.uniform(60, 120, n), bw_v_deg=rng.uniform(40, 90, n),
        di_db=rng.uniform(8, 14, n), di_source="balloon",
        ripple_h_db=ripple, ripple_v_db=rng.uniform(0.2, 2.0, n),
        on_axis_db=rng.normal(0, 1, n), z_throat_real=np.real(resp.z_throat),
        scalars={"n_freqs": n, "di_source": "balloon", "bw_h_mean_deg": float(np.nanmean(rng.uniform(60, 120, n))),
                 "di_slope_db_per_dec": float(rng.normal(0, 1)), "f_break_h_hz": float("nan"),
                 "ripple_mean_db": np.float64(1.0), "n_multilobe_h": np.int64(0)})
    mesh = MeshResult(path="x.msh", n_triangles=4586, n_dof=2369, quadrants="1", symmetry_plane="yz+xz",
                      res_mm={"throat": 3.0, "mouth": 6.0, "rear": 6.0},
                      bbox_m=(0.0, 0.0, 0.0, 0.1, 0.1, 0.15), seconds=1.5)
    out = SolveOutcome(ok=True, response=resp, seconds=5.0, peak_vram_mb=1642.0)
    return Evaluation(design_hash=dh, design=design, mesh_hash="m" + dh[1:], solve_hash="s" + dh[1:],
                      objective=float(rng.uniform(1, 5)) if objective is None else objective,
                      terms={"cov": 1.0, "rip": 0.5, "di": 0.1, "dislope": 0.0, "flat": 0.2,
                             "load": 0.0, "penalty": 0.0, "total": 1.8, "nan_count": np.int64(1)},
                      metrics=ms, mesh=mesh, outcome=out)


def trace_arrays(nf: int = 12, n_vertices: int = 2369, n_faces: int = 4586) -> dict:
    """Surface traces at TOOLCHAIN.md C2b sizes: 111,280 bytes per frequency at 2,369 dofs."""
    rng = np.random.default_rng(7)
    return {
        "surface_pressure_complex": rng.normal(size=(nf, n_vertices)) + 1j * rng.normal(size=(nf, n_vertices)),
        "surface_neumann_complex": rng.normal(size=(nf, n_faces)) + 1j * rng.normal(size=(nf, n_faces)),
    }
