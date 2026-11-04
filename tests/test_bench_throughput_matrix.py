"""WP0/WP5: tools/bench/throughput_matrix.py and tools/bench/_hosts.py, offline (fake solver)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

from conftest import EXAMPLES, REPO

sys.path.insert(0, str(REPO / "tools" / "bench"))
import _hosts  # noqa: E402
import throughput_matrix as tm  # noqa: E402

CFG = str(EXAMPLES / "osse_baseline_fusedcuda.yaml")


def test_parse_lists():
    assert tm.parse_int_list("12, 25,36") == [12, 25, 36]
    assert tm.parse_batch_sizes("default,1,2,4,12") == [None, 1, 2, 4, 12]
    assert tm.parse_batch_sizes("0") == [None]
    with pytest.raises(ValueError):
        tm.parse_batch_sizes("-3")
    with pytest.raises(ValueError):
        tm.parse_batch_sizes(" , ")
    assert tm.batch_label(None) == "default" and tm.batch_label(4) == "b4"


def test_frequency_sets_match_production_grids_and_never_drop_points():
    from hornlab_search.config import load_config, mode_freqs
    cfg = load_config(CFG)
    assert tm.resolve_freq_set("12", cfg) == tuple(mode_freqs("screen", cfg))
    assert tm.resolve_freq_set("25", cfg) == tuple(mode_freqs("verify", cfg))
    assert tm.resolve_freq_set("36", cfg) == tuple(mode_freqs("final", cfg))
    f41 = tm.resolve_freq_set("41", cfg)
    assert len(f41) == 41 and f41[0] == 120.0 and f41[-1] == 12000.0
    assert len(tm.resolve_freq_set("100:1000:5", cfg)) == 5


def test_summary_math():
    s = tm.summarize_values([10.0, 12.0, 11.0, None, float("nan")])
    assert s["n"] == 3 and s["median"] == 11.0 and s["min"] == 10.0 and s["max"] == 12.0
    assert s["rel_spread"] == pytest.approx(2.0 / 11.0)
    assert tm.summarize_values([])["median"] is None
    assert tm.candidates_per_hour(36.0) == pytest.approx(100.0)
    assert tm.candidates_per_hour(0) is None
    assert tm.speedup(20.0, 10.0) == pytest.approx(2.0) and tm.speedup(None, 1.0) is None


def test_summarize_arm_uses_warm_reps_only_and_counts_failures():
    rows = [{"rep": "cold", "ok": True, "wall_s": 50.0, "solve_s": 49.0, "n_freqs": 12,
             "host_start_s": 7.0},
            {"rep": 1, "ok": True, "wall_s": 10.0, "solve_s": 9.5, "n_freqs": 12},
            {"rep": 2, "ok": True, "wall_s": 12.0, "solve_s": 11.0, "n_freqs": 12},
            {"rep": 3, "ok": False, "wall_s": 99.0, "solve_s": 1.0, "n_freqs": 12}]
    a = tm.summarize_arm(rows)
    assert a["warm"]["median"] == 11.0 and a["cold_wall_s"] == 50.0 and a["failures"] == 1
    assert a["s_per_freq_median"] == pytest.approx(11.0 / 12) and a["warm_start_s"] == 7.0
    assert a["candidates_per_hour_warm"] == pytest.approx(3600 / 11.0)


def test_plan_arms_covers_everything_and_rotates():
    arms = tm.plan_arms([{"label": "m"}], ["12", "25"], [None, 1, 4])
    assert len(arms) == 6
    assert {(a["freq_set"], a["batch"]) for a in arms} == {(f, b) for f in ("12", "25")
                                                            for b in (None, 1, 4)}
    assert [a["batch"] for a in arms[:3]] != [a["batch"] for a in arms[3:]]   # rotated


def test_parity_flags_differences():
    import numpy as np
    a = {"freqs_hz": np.arange(3.0), "spl_h_db": np.zeros((3, 2)), "spl_v_db": np.zeros((3, 2)),
         "spl_balloon_db": None, "z_throat": np.ones(3) * (1 + 1j)}
    b = {**a, "spl_h_db": np.full((3, 2), 0.25)}
    p = tm.parity(a, b)
    assert p["freqs_equal"] and p["shape_equal"] and p["max_abs_spl_h_db"] == 0.25
    assert tm.parity(a, None) == {"compared": False}
    c = {**a, "freqs_hz": np.arange(3.0) + 1}
    assert not tm.parity(a, c)["freqs_equal"]


def test_nvidia_poller_runs_in_its_own_thread_and_windows(monkeypatch):
    import threading
    import time
    seen_threads = set()
    vals = iter([(500, 8188, 1), (900, 8188, 80), (4000, 8188, 95), (700, 8188, 5)] * 50)

    def q():
        seen_threads.add(threading.current_thread().name)
        return next(vals)
    p = tm.NvidiaSmiPoller(period_s=0.01, query=q).start()
    t0 = time.monotonic()
    time.sleep(0.15)
    t1 = time.monotonic()
    p.stop()
    w = p.window(t0, t1)
    assert seen_threads == {"nvidia-smi-poller"}
    assert w["smi_peak_mib"] == 4000 and w["smi_samples"] > 0 and p.total_mib == 8188
    assert w["smi_baseline_mib"] is not None


def test_nvidia_poller_without_smi_is_just_empty(monkeypatch):
    p = tm.NvidiaSmiPoller(period_s=0.01, query=lambda: None).start()
    p.stop()
    assert p.samples == [] and p.window(0, 1)["smi_peak_mib"] is None


def test_production_solve_spec_keeps_the_production_extra_and_only_swaps_freqs():
    from hornlab_search.config import load_config, solve_spec
    cfg = load_config(CFG)
    prod = solve_spec("screen", cfg)
    mine = tm.production_solve_spec(cfg, "screen", (500.0, 1000.0))
    assert mine.freqs_hz == (500.0, 1000.0)
    assert dict(mine.extra) == dict(prod.extra) and mine.extra.get("cuda_fused") is True
    assert mine.observation == prod.observation and mine.backend == prod.backend


def test_mesh_from_msh_takes_the_symmetry_from_the_config(tmp_path):
    from hornlab_search.config import load_config
    from hornlab_search.search.selftest import icosphere, write_sphere_msh
    cfg = load_config(CFG)
    pts, tris = icosphere(0.1, 0)
    msh = tmp_path / "m.msh"
    write_sphere_msh(pts, tris, msh)
    m = tm.mesh_from_msh(msh, cfg)
    from hornlab_search.mesh import sizing
    assert m.symmetry_plane == sizing.SYMMETRY_PLANE[cfg.mesh.quadrants]
    assert m.quadrants == cfg.mesh.quadrants


def test_cli_dry_run_solves_nothing(capsys):
    rc = tm.main(["--config", CFG, "--fake", "--dry-run", "--freq-sets", "12,41",
                  "--batch-sizes", "default,1,4"])
    out = capsys.readouterr().out
    assert rc == 0 and "6 arms" in out and "freqs=41(41)" in out


def test_cli_requires_a_fixture(capsys):
    assert tm.main(["--config", CFG]) == 2


def test_cli_fake_run_writes_the_outputs_with_parity_and_no_dropped_frequencies(tmp_path):
    out = tmp_path / "o"
    rc = tm.main(["--config", CFG, "--fake", "--freq-sets", "12,41", "--batch-sizes",
                  "default,1,4", "--warm-reps", "2", "--out", str(out)])
    assert rc == 0
    for name in ("results.csv", "summary.csv", "summary.json", "env.json"):
        assert (out / name).exists()
    rows = list(csv.DictReader(open(out / "results.csv", encoding="utf-8")))
    assert len(rows) == 2 * 3 * 3                                   # 2 freq sets x 3 batches x (cold+2)
    assert {r["n_freqs"] for r in rows} == {"12", "41"}
    assert all(r["cuda_fused"] == "True" and r["ok"] == "True" for r in rows)
    summ = json.loads((out / "summary.json").read_text())
    assert summ["reference_batch"] == "default" and len(summ["arms"]) == 6
    for a in summ["arms"]:
        if a["batch"] != "default":
            assert a["parity_vs_default"]["max_abs_spl_h_db"] == 0.0
    env = json.loads((out / "env.json").read_text())
    assert "git_sha" in env and "python" in env and "platform" in env


def test_fake_backend_call_groups_follow_the_batch_size():
    f = tm.FakeBackend(batch=4)
    from hornlab_search.config import load_config
    cfg = load_config(CFG)
    spec = tm.production_solve_spec(cfg, "screen", tm.resolve_freq_set("12", cfg))
    out = f.solve(None, spec)
    assert out.ok and f.calls == 3 and len(out.response.freqs_hz) == 12


# ---------------------------------------------------------------- _hosts.py


class P:
    def __init__(self, pid):
        self.pid = pid


def test_kill_hosts_only_kills_hosts_started_after_the_snapshot():
    _hosts.reset_for_tests()
    live = [P(100), P(101)]                    # pre-existing (someone else's)
    killed = []
    assert _hosts.kill_hosts(lister=lambda: list(live), killer=lambda pid: killed.append(pid),
                             sleep=lambda s: None) == []        # first call = snapshot, kills nothing
    assert killed == []
    live.append(P(200))                        # started by "this script"
    got = _hosts.kill_hosts(lister=lambda: list(live), killer=lambda pid: killed.append(pid),
                            sleep=lambda s: None)
    assert got == [200] and killed == [200]
    _hosts.reset_for_tests()


def test_no_taskkill_by_image_name_remains_in_the_bench_scripts():
    for f in (REPO / "tools" / "bench").glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "taskkill" not in text.replace("taskkill /IM", "").replace("`taskkill", ""), f
        assert '"/IM"' not in text, f


def test_bench_solve_kwargs_default_is_legacy(monkeypatch):
    monkeypatch.delenv("HORNLAB_BENCH_SYMMETRY", raising=False)
    monkeypatch.delenv("HORNLAB_BENCH_FUSED", raising=False)
    assert _hosts.bench_solve_kwargs() == {}
    monkeypatch.setenv("HORNLAB_BENCH_SYMMETRY", "yz+xz")
    monkeypatch.setenv("HORNLAB_BENCH_FUSED", "1")
    try:
        assert _hosts.bench_solve_kwargs() == {"native_symmetry_plane": "yz+xz"}
        import os
        assert os.environ["HORNLAB_BEAT_FUSED_BM_CUDA"] == "1"
    finally:
        import os
        os.environ.pop("HORNLAB_BEAT_FUSED_BM_CUDA", None)
