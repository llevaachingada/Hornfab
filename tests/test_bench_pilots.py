"""WP3 / WP4 bench tools (offline): cpu_gpu_concurrent.py and mesh_policy_study.py pure logic + fake mode."""
from __future__ import annotations

import json
import sys

import numpy as np
import pytest

from conftest import EXAMPLES, REPO

sys.path.insert(0, str(REPO / "tools" / "bench"))
import cpu_gpu_concurrent as cg  # noqa: E402
import mesh_policy_study as mps  # noqa: E402

CFG = str(EXAMPLES / "osse_baseline_fusedcuda.yaml")


class PI:
    def __init__(self, pid, ppid, name="x", cmdline=""):
        self.pid, self.ppid, self.name, self.cmdline = pid, ppid, name, cmdline


def test_descends_from_and_own_host_roots_exclude_the_other_lane():
    from hornlab_search.solve import worker
    M = worker.HOST_MARKER
    procs = [PI(1, 0), PI(10, 1), PI(11, 10, "python", f"python -m {M}"),      # lane A tree
             PI(20, 1), PI(21, 20, "python", f"python -m {M}")]                # lane B tree
    assert cg.descends_from(procs, 11, 10) and not cg.descends_from(procs, 21, 10)
    mine = cg.own_host_roots(procs, 10)
    assert [p.pid for p in mine] == [11]
    assert [p.pid for p in cg.own_host_roots(procs, 20)] == [21]


def test_lane_env_isolates_worker_dir_and_limits_cpu_threads_only_for_the_cpu_lane(tmp_path):
    base = {"PATH": "x"}
    cpu = cg.lane_env("cpu", tmp_path, cpu_threads=4, base=base)
    gpu = cg.lane_env("cuda", tmp_path, cpu_threads=4, base=base)
    assert cpu["HORNLAB_BEAT_WORKER_DIR"] != gpu["HORNLAB_BEAT_WORKER_DIR"]
    assert cpu["JULIA_NUM_THREADS"] == "4" and "JULIA_NUM_THREADS" not in gpu
    assert base == {"PATH": "x"}                                   # the caller's env is not mutated


def _lane(name, t0, per, n=3, ok=True, fp_shift=0.0):
    fps = [{"freqs_hz": np.arange(3.0), "spl_h_db": np.zeros((3, 2)) + fp_shift,
            "spl_v_db": np.zeros((3, 2)), "spl_balloon_db": None, "z_throat": None} for _ in range(n)]
    return {"lane": name, "candidates": [{"i": i, "ok": ok, "seconds": per} for i in range(n)],
            "t_start": t0, "t_end": t0 + per * n, "fingerprints": fps}


def test_aggregate_report_math():
    serial = {"cuda": _lane("cuda", 0, 10.0), "cpu": _lane("cpu", 0, 25.0)}
    conc = {"cuda": _lane("cuda", 100, 11.0), "cpu": _lane("cpu", 100, 27.0)}   # window 81 s, 6 cands
    r = cg.aggregate_report(serial, conc)
    assert r["window_s"] == pytest.approx(81.0)
    assert r["aggregate_candidates_per_hour"] == pytest.approx(3600 / (81.0 / 6))
    assert r["candidates_per_hour_alone"]["cuda"] == pytest.approx(3600 / 10.0)
    assert r["ideal_sum_candidates_per_hour"] == pytest.approx(360 + 144)
    assert r["gain_vs_gpu_alone"] == pytest.approx(r["aggregate_candidates_per_hour"] / 360)
    assert r["cuda_slowdown"] == pytest.approx(1.1)
    assert r["parity"]["cuda"]["ok"] and r["parity"]["cuda"]["n_compared"] == 3


def test_aggregate_report_flags_parity_failures_and_never_hints_adoption_on_them():
    serial = {"cuda": _lane("cuda", 0, 10.0), "cpu": _lane("cpu", 0, 10.0)}
    conc = {"cuda": _lane("cuda", 100, 10.0), "cpu": _lane("cpu", 100, 10.0, fp_shift=1.0)}
    r = cg.aggregate_report(serial, conc)
    assert not r["parity"]["cpu"]["ok"] and r["parity"]["cpu"]["max_abs_spl_db"] == 1.0
    assert r["adopt_hint"] is False
    bad = {"cuda": _lane("cuda", 100, 10.0), "cpu": _lane("cpu", 100, 10.0, ok=False)}
    assert cg.aggregate_report(serial, bad)["adopt_hint"] is False


def test_fake_concurrent_run_end_to_end(tmp_path, capsys):
    rc = cg.main(["--config", CFG, "--fake", "--n-per-lane", "2", "--out", str(tmp_path)])
    assert rc == 0
    rep = json.loads((tmp_path / "report.json").read_text())
    assert rep["parity"]["cuda"]["ok"] and rep["parity"]["cpu"]["ok"]
    assert rep["concurrent_per_lane"]["cuda"]["failures"] == 0
    assert rep["plan"]["isolation"].startswith("separate processes")


def test_dry_run_and_missing_mesh(tmp_path, capsys):
    assert cg.main(["--config", CFG, "--dry-run", "--mesh-gpu", "a.msh", "--out", str(tmp_path)]) == 0
    assert cg.main(["--config", CFG]) == 2


# ---------------------------------------------------------------- mesh_policy_study


def test_edge_stats_on_a_unit_square_two_triangles():
    xyz = np.array([[0, 0, 0], [0.001, 0, 0], [0.001, 0.001, 0], [0, 0.001, 0.0]])
    tri = np.array([[0, 1, 2], [0, 2, 3]])
    s = mps.edge_stats(xyz, tri)
    assert s["n_edges"] == 5 and s["edge_min_mm"] == pytest.approx(1.0)
    assert s["edge_max_mm"] == pytest.approx(2 ** 0.5)


def test_compare_and_parse():
    arms = [{"n_vertices": 1000, "n_triangles": 2000, "build_s": 2.0},
            {"n_vertices": 700, "n_triangles": 1400, "build_s": 3.0}]
    mps.compare_to_baseline(arms)
    assert arms[1]["N_ratio"] == 0.7 and arms[1]["E_ratio"] == 0.7 and arms[1]["build_time_ratio"] == 1.5
    assert mps.parse_curvatures("12,20") == [0.0, 12.0, 20.0]      # baseline always first
    assert mps.parse_curvatures("0,8") == [0.0, 8.0]
    with pytest.raises(ValueError):
        mps.parse_curvatures("-1")
    with pytest.raises(ValueError):
        mps.parse_curvatures("")


def test_compare_search_runs(tmp_path):
    import compare_search_runs as csr
    rows = [{"n": i, "design_hash": f"d{i}", "objective": float(i), "terms": {"t": 1.0}, "ok": True,
             "cached": False, "seconds": {"total": 1.0 + i}} for i in range(3)]
    other = [dict(r, seconds={"total": 9.0}) for r in rows]
    assert csr.compare_rows(rows, other) == []                    # timing is ignored
    other[1]["objective"] = 5.0
    assert "objective" in csr.compare_rows(rows, other)[0]
    assert csr.compare_rows(rows, rows[:2])[0].startswith("row count")
    for name, rr in (("a", rows), ("b", rows)):
        d = tmp_path / name
        d.mkdir()
        (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rr) + "\n")
    assert csr.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 0
