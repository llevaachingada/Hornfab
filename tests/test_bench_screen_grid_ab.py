"""Offline tests for tools/bench/screen_grid_ab.py (no solver, no GPU).

The GPU measurement itself is validated by the queued night jobs; these tests pin the parts that
decide what the experiment MEANS: the arm frequency nesting, the ranking statistic, the HF defect
detector, and the CSV row contract (a missing column silently empties the analysis).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "screen_grid_ab", REPO / "tools" / "bench" / "screen_grid_ab.py")
assert _spec and _spec.loader
ab = importlib.util.module_from_spec(_spec)
sys.modules["screen_grid_ab"] = ab
_spec.loader.exec_module(ab)

from hornlab_search.config import freq_grid, load_config  # noqa: E402


def test_arms_are_nested_and_hf_weighted():
    f = ab.arm_freqs()
    assert f["F0"] is None                     # frozen grid, resolved by the config
    for arm in ("F0M", "F1", "F2", "FA", "FB", "F3"):
        assert f[arm] == tuple(sorted(f[arm])), arm
    f0 = tuple(float(x) for x in freq_grid(500.0, 10_000.0, 12))
    # the dense reference contains the two uniform arms exactly, so their J difference against
    # the reference is a pure sampling error (same mesh, same scoring definition)
    for fs in (f["F1"], f["F2"]):
        assert set(fs) <= set(f["F3"])
    # the additive arms add the same 8-12 kHz comb to different bases
    comb = set(f["FA"]) - set(f0)
    assert comb <= set(f["F3"]) and comb <= set(f["FB"])
    assert len(f["F0M"]) == len(f0) + 1
    assert f["F0M"][-1] == 12_000.0
    # 4 and 6 points/octave put only two samples above 10 kHz: the reason FA/FB exist
    assert len([x for x in f["F1"] if x > 10_000]) == 2
    assert len([x for x in f["F2"] if x > 10_000]) == 2
    assert len([x for x in f["FA"] if x > 10_000]) >= 4
    assert len([x for x in f["FB"] if x > 10_000]) >= 4
    for fs in (f["F0M"], f["F1"], f["F2"], f["FA"], f["FB"], f["F3"]):
        assert max(fs) == 12_000.0


def test_spearman_edges():
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert abs(ab._spearman(a, a) - 1.0) < 1e-12
    assert abs(ab._spearman(a, -a) + 1.0) < 1e-12
    assert np.isnan(ab._spearman(a[:2], a[:2]))


def _arrays(freqs, oa, bw=None, di=None):
    arrs = {"f": np.asarray(freqs, float), "oa_h": np.asarray(oa, float),
            "oa_v": np.asarray(oa, float)}
    if bw is not None:
        arrs["bw_h_deg"] = np.asarray(bw, float)
    if di is not None:
        arrs["di_db"] = np.asarray(di, float)
    return arrs


def test_hf_flags_detect_a_notch_and_a_collapse():
    f = np.array([1000, 2000, 4000, 6000, 8000, 9000, 10000, 11000, 12000.0])
    smooth = np.array([90, 90, 90, 90, 90, 90, 90, 90, 90.0])
    flags = ab._hf_flags(_arrays(f, smooth, bw=np.full(9, 60.0), di=np.full(9, 10.0)))
    assert flags["hf_ripple_db"] < 1e-9
    assert flags["hf_notch_db"] < 1e-9
    assert abs(flags["hf_bw_ratio"] - 1.0) < 1e-9

    notched = smooth.copy()
    notched[6] = 78.0                                    # 12 dB dip at 10 kHz
    flags = ab._hf_flags(_arrays(f, notched))
    assert flags["hf_notch_db"] >= 6.0
    assert flags["hf_ripple_db"] >= 6.0

    bw = np.array([60, 60, 60, 60, 55, 40, 35, 30, 30.0])
    flags = ab._hf_flags(_arrays(f, smooth, bw=bw))
    assert flags["hf_bw_ratio"] <= 0.6


def test_row_contract_includes_every_analysis_column():
    fields = set(ab.MEASURE_FIELDS)
    for key in ("wall_s", "J", "n_dof", "solve_s", "gpu_used_peak_mib", "gpu_baseline_mib",
                "response", "term_total", "term_cd_lw", "di_source", "f11_hz"):
        assert key in fields, key
    assert ab.ARMS == ("F0", "F0M", "F1", "F2", "FA", "FB", "F3")


@pytest.fixture
def arm_cfg(tmp_path):
    raw = copy.deepcopy(yaml.safe_load(
        (REPO / "examples" / "osse_baseline.yaml").read_text(encoding="utf-8")))
    raw["target"]["band_hi_hz"] = 12000.0
    raw["solve"]["screen_grid"] = {"freqs_hz": [500, 1000, 2000, 4000, 8000, 12000]}
    p = tmp_path / "arm.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_row_from_eval_reads_the_production_fields(tmp_path, arm_cfg):
    class _Mesh:
        n_dof = 4321
        n_triangles = 8765
        seconds = 2.5

    class _Outcome:
        seconds = 11.5
        peak_vram_mb = 700.0

    terms = {"total": 1.5, "cov_profile": 0.1, "rip": 0.2, "flat": 0.3, "dislope": 0.4,
             "di_roughness": 0.5, "load": 0.6, "flat_cv": 0.7, "hf_floor": 0.0,
             "cd_lw": 0.8, "cd_di_std": 0.9, "cd_nacc": 1.0, "offaxis_smooth": 1.1,
             "n_in_band": 6}
    metrics = SimpleNamespace(di_source="balloon", bw_h_mean_deg=70.0, bw_v_mean_deg=60.0,
                              di_mean_db=10.0, di_slope_db_per_dec=1.0, ripple_mean_db=1.2,
                              f_break_h_hz=800.0, f_break_v_hz=900.0, f11_hz=5600.0,
                              spdi_mean_db=9.0, spdi_range_db=3.0)
    ev = SimpleNamespace(design_hash="abc", objective=2.5, terms=terms, metrics=metrics,
                         mesh=_Mesh(), outcome=_Outcome(), cached=False, error="")
    row = ab._row_from_eval({"id": "co"}, {"label": "n1"}, "F1", ev, arm_cfg,
                            SimpleNamespace(peak_mib=2000.0, baseline_mib=1900.0), tmp_path)
    assert row["cohort"] == "co" and row["arm"] == "F1"
    assert row["n_freqs"] == 6 and row["f_max_hz"] == 12000.0
    assert row["n_dof"] == 4321 and row["solve_s"] == 11.5
    assert row["J"] == 2.5 and row["term_cd_lw"] == 0.8 and row["n_in_band"] == 6
    assert row["di_source"] == "balloon" and row["f11_hz"] == 5600.0
    assert row["gpu_used_peak_mib"] == 2000.0


@pytest.mark.slow
def test_measure_plumbing_end_to_end_with_a_synthetic_backend(tmp_path, monkeypatch):
    """The unattended night job runs `_run_measure`; this pins its wiring (manifest -> evaluate
    -> CSV) with a synthetic solver.  No GPU, no Julia host, one CPU mesh build."""
    import types as _types

    from conftest import REPO as _REPO
    from test_search_support import SyntheticBackend
    from hornlab_search.types import Design

    base = copy.deepcopy(yaml.safe_load(
        (_REPO / "examples" / "osse_baseline.yaml").read_text(encoding="utf-8")))
    base["target"]["band_hi_hz"] = 12000.0
    base.setdefault("solve", {})
    base["solve"]["balloon"] = False
    base.setdefault("mesh", {})["dof_cap_screen"] = 30000   # a 12 kHz mesh doubles the dofs
    base.setdefault("mesh", {})["dof_cap_screen"] = 30000   # a 12 kHz mesh doubles the dofs
    params = base["seed_params"]
    family = base["family"]
    dh = Design(family, params).hash()
    configs = {}
    for arm, grid in (("F0", None), ("F1", {"freqs_hz": [500, 1000, 2000, 4000, 8000, 12000]})):
        raw = copy.deepcopy(base)
        if grid is not None:
            raw["solve"]["screen_grid"] = grid
        p = tmp_path / f"{arm}.yaml"
        p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        configs[arm] = str(p)
    out = tmp_path / "exp"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps({"cohorts": [{
        "id": "smoke", "class": "test",
        "designs": [{"design_hash": dh, "label": "seed", "family": family, "params": params,
                     "seed_objective": 0.0}],
        "arm_configs": configs}]}), encoding="utf-8")

    stub = _types.ModuleType("hornlab_search.solve.worker")
    stub.install_handlers = lambda: None
    stub.warm = lambda backend: None
    stub.shutdown = lambda **kw: None
    monkeypatch.setitem(sys.modules, "hornlab_search.solve.worker", stub)
    monkeypatch.setenv("HORNLAB_GPU_LOCK", "off")
    monkeypatch.setattr(ab, "_backend_for", lambda cfg: SyntheticBackend())

    args = _types.SimpleNamespace(out=str(out), cohorts=["smoke"], arms=["F0", "F1"],
                                  force=True)
    rc = ab._run_measure(args)
    assert rc == 0
    rows = ab._read_csv(out / "measurements.csv")
    assert len(rows) == 2
    assert {r["arm"] for r in rows} == {"F0", "F1"}
    assert all(r["cohort"] == "smoke" for r in rows)
    assert all(r["n_dof"] and float(r["n_dof"]) > 0 for r in rows)
    assert any(float(r["f_max_hz"]) == 12000.0 for r in rows)


def test_analyze_writes_the_evidence_tables(tmp_path):
    """Analyze is the unattended tail of the chain; it must produce every requested CSV from a
    measurements.csv + response.npz, with a ranking that notices a reversed screen."""
    import csv

    from test_search_support import synthetic_response

    base = copy.deepcopy(yaml.safe_load(
        (REPO / "examples" / "osse_baseline.yaml").read_text(encoding="utf-8")))
    base["target"]["band_hi_hz"] = 12000.0
    base.setdefault("solve", {})
    base["solve"]["balloon"] = False
    base.setdefault("mesh", {})["dof_cap_screen"] = 30000
    out, ev = tmp_path / "exp", tmp_path / "evidence"
    out.mkdir()
    ev.mkdir()
    arms = {"F0": None, "F1": [500, 1000, 2000, 4000, 8000, 12000],
            "F3": [500, 700, 1000, 1400, 2000, 2800, 4000, 5600, 8000, 9000, 10000, 11000, 12000]}
    configs = {}
    for arm, grid in arms.items():
        raw = copy.deepcopy(base)
        if grid is not None:
            raw["solve"]["screen_grid"] = {"freqs_hz": grid}
        p = tmp_path / f"{arm}.yaml"
        p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        configs[arm] = str(p)
    designs = [{"design_hash": f"d{i}", "label": f"n{i}", "family": base["family"],
                "params": dict(base["seed_params"], a_deg=30.0 + 5 * i), "seed_objective": 0.0}
               for i in range(3)]
    (out / "manifest.json").write_text(json.dumps({"cohorts": [{
        "id": "co", "class": "t", "designs": designs, "arm_configs": configs}]}), encoding="utf-8")

    rows = []
    # F3 is the truth: better design = lower J. F0 sees the order reversed.
    j_truth = {"d0": 1.0, "d1": 2.0, "d2": 3.0}
    for arm, grid in arms.items():
        for d in designs:
            freqs = grid or [500, 1000, 2000, 4000, 8000]
            resp = synthetic_response(d["params"], freqs)
            p = out / f"{arm}_{d['design_hash']}.npz"
            np.savez(p, freqs_hz=resp.freqs_hz, h_angles_deg=resp.h_angles_deg,
                     v_angles_deg=resp.v_angles_deg, spl_h_db=resp.spl_h_db,
                     spl_v_db=resp.spl_v_db, balloon_dirs=resp.balloon_dirs,
                     spl_balloon_db=resp.spl_balloon_db, z_throat=resp.z_throat,
                     p_h=resp.p_h, p_v=resp.p_v, p_balloon=resp.p_balloon,
                     backend="synthetic")
            j = j_truth[d["design_hash"]]
            if arm == "F0":
                j = 4.0 - j                                # reversed ranking
            rows.append({"cohort": "co", "design_hash": d["design_hash"],
                         "design_label": d["label"], "arm": arm, "n_freqs": len(freqs),
                         "f_max_hz": max(freqs), "n_dof": 4000, "n_triangles": 8000,
                         "ok": "True", "error": "", "J": j, "cached": "False",
                         "solve_s": 10.0 + len(freqs), "mesh_s": 1.0, "wall_s": 12.0 + len(freqs),
                         "gpu_used_peak_mib": 2000.0, "gpu_baseline_mib": 1900.0,
                         "response": str(p), "config": configs[arm], "di_source": "cuts_estimate"})
    with open(out / "measurements.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ab.MEASURE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    args = SimpleNamespace(out=str(out), evidence=str(ev))
    assert ab.cmd_analyze(args) == 0
    for name in ("FREQUENCY_REFERENCE.csv", "GPU_BENCHMARK.csv", "FREQUENCY_GRID_AB.csv",
                 "SCREEN_RANKING.csv", "HF_FAILURES.csv", "summary.json"):
        assert (ev / name).exists(), name
    ranking = ab._read_csv(ev / "SCREEN_RANKING.csv")
    f0 = [r for r in ranking if r["arm"] == "F0"][0]
    assert float(f0["spearman_vs_ref"]) < 0        # the reversed screen is caught
    # n=3 makes top-3 overlap trivially full; the statistic is only informative on the 6-design
    # cohorts, so assert its shape rather than a value here
    assert int(f0["top3_overlap"]) == 3
    ab_rows = ab._read_csv(ev / "FREQUENCY_GRID_AB.csv")
    assert len(ab_rows) == 9
    assert any(float(r["dJ_vs_ref"]) == 0.0 for r in ab_rows if r["arm"] == "F3")


def test_report_applies_the_pre_registered_rule(tmp_path):
    """`report` must not crash on partial evidence and must emit one verdict row per arm."""
    import csv

    from test_search_support import synthetic_response

    base = copy.deepcopy(yaml.safe_load(
        (REPO / "examples" / "osse_baseline.yaml").read_text(encoding="utf-8")))
    base["target"]["band_hi_hz"] = 12000.0
    base.setdefault("solve", {})["balloon"] = False
    base.setdefault("mesh", {})["dof_cap_screen"] = 30000
    out, ev = tmp_path / "exp", tmp_path / "evidence"
    out.mkdir()
    ev.mkdir()
    arms = {"F0": None, "F1": [500, 1000, 2000, 4000, 8000, 12000],
            "F3": [500, 700, 1000, 1400, 2000, 2800, 4000, 5600, 8000, 9000, 10000, 11000, 12000]}
    configs = {}
    for arm, grid in arms.items():
        raw = copy.deepcopy(base)
        if grid is not None:
            raw["solve"]["screen_grid"] = {"freqs_hz": grid}
        p = tmp_path / f"{arm}.yaml"
        p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        configs[arm] = str(p)
    designs = [{"design_hash": f"d{i}", "label": f"n{i}", "family": base["family"],
                "params": dict(base["seed_params"], a_deg=30.0 + 5 * i), "seed_objective": 0.0}
               for i in range(3)]
    (out / "manifest.json").write_text(json.dumps({"cohorts": [{
        "id": "co", "class": "t", "designs": designs, "arm_configs": configs}]}), encoding="utf-8")
    rows = []
    for arm, grid in arms.items():
        for d in designs:
            freqs = grid or [500, 1000, 2000, 4000, 8000]
            resp = synthetic_response(d["params"], freqs)
            p = out / f"{arm}_{d['design_hash']}.npz"
            np.savez(p, freqs_hz=resp.freqs_hz, h_angles_deg=resp.h_angles_deg,
                     v_angles_deg=resp.v_angles_deg, spl_h_db=resp.spl_h_db,
                     spl_v_db=resp.spl_v_db, balloon_dirs=resp.balloon_dirs,
                     spl_balloon_db=resp.spl_balloon_db, z_throat=resp.z_throat,
                     p_h=resp.p_h, p_v=resp.p_v, p_balloon=resp.p_balloon, backend="synthetic")
            rows.append({"cohort": "co", "design_hash": d["design_hash"],
                         "design_label": d["label"], "arm": arm, "n_freqs": len(freqs),
                         "f_max_hz": max(freqs), "n_dof": 4000, "n_triangles": 8000,
                         "ok": "True", "error": "", "J": 2.0 + ord(d["design_hash"][1]) % 3,
                         "cached": "False", "solve_s": 10.0 + len(freqs), "mesh_s": 1.0,
                         "wall_s": 12.0 + len(freqs), "gpu_used_peak_mib": 2000.0,
                         "gpu_baseline_mib": 1900.0, "response": str(p), "config": configs[arm],
                         "di_source": "cuts_estimate"})
    with open(out / "measurements.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ab.MEASURE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    assert ab.cmd_analyze(SimpleNamespace(out=str(out), evidence=str(ev))) == 0
    assert ab.cmd_report(SimpleNamespace(out=str(out), evidence=str(ev))) == 0
    table = ab._read_csv(ev / "DECISION_TABLE.csv")
    assert {r["arm"] for r in table} == {"F0", "F1", "F3"}
    for col in ("c1_pass", "c2_pass", "c3_pass", "c4_pass", "all_pass"):
        assert col in table[0]
    rep = json.loads((ev / "DECISION_REPORT.json").read_text(encoding="utf-8"))
    assert rep["ref"] == "F3" and "cheapest_passing_arm" in rep
