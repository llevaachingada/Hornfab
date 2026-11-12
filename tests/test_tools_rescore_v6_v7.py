"""Offline tests for tools/rescore/rescore_v6_v7.py and tools/rescore/driver_check.py.

NO GPU, NO solver, NO dataset writes: the dataset pipeline is exercised on a synthetic stored
row (the same JSONL-row + NPZ-arrays shape the real records carry), and the two real briefs
(``campaign_2026-10-26_v6`` / ``hardened_2026-10-29_v5``, version 7) are loaded from the repo.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import sys

import numpy as np
import pytest

from conftest import REPO

from hornlab_search.targets.spec import Target

_RESORE_TOOL = REPO / "tools" / "rescore" / "rescore_v6_v7.py"
_DRIVER_TOOL = REPO / "tools" / "rescore" / "driver_check.py"


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rv = _load_tool("rescore_v6_v7_tool", _RESORE_TOOL)
dc = _load_tool("driver_check_tool", _DRIVER_TOOL)


# ------------------------------------------------------------------ targets / classifier


def _target(**kw) -> Target:
    base: dict = dict(coverage_h_deg=90.0, coverage_v_deg=60.0, band_lo_hz=300.0,
                      band_hi_hz=8000.0, di_target_db=8.0, di_slope_target=0.0, z_min=0.7,
                      f0_hz=600.0, driver_exit_radius_mm=18.0)
    base.update(kw)
    return Target(**base)


def test_classify_target_b_loading_scored():
    assert rv.classify_target(_target()) == "B"          # z_min 0.7 >= 0.5
    assert rv.classify_target(_target(z_min=0.0, di_slope_target=3.0)) == "B"  # rising-DI target


def test_classify_target_c_low_reach():
    t = _target(z_min=0.0, f0_hz=400.0)
    assert rv.classify_target(t) == "C"


def test_classify_target_a_cd():
    t = _target(z_min=0.0, f0_hz=850.0)
    assert rv.classify_target(t) == "A"


def test_target_key_format():
    assert rv.target_key(_target()) == "90x60_300-8000_f0=600"
    no_f0 = _target(f0_hz=None)
    assert rv.target_key(no_f0).endswith("_f0=none")


# ------------------------------------------------------------------ briefs


def test_load_brief_v6():
    cfg = rv.load_brief(rv.V6_BRIEF)
    assert cfg.version == 6
    assert cfg.weights["load_near"] == 1.0
    assert cfg.params.tolerances["load_near"] == 0.25
    assert cfg.params.pattern_beta == 1.6
    assert cfg.params.fc_hz is None


def test_load_brief_v7_all_classes():
    v7 = rv.brief_configs()[7]
    assert set(v7) == {"A", "B", "C"}
    for cls, cfg in v7.items():
        assert cfg.version == 7
    # The briefs really are class-specific: the B brief has the loading weight, A does not need it.
    assert v7["B"].weights["load"] == 1.0


def test_brief_configs_shape():
    briefs = rv.brief_configs()
    assert set(briefs) == {6, 7}
    assert briefs[6]["A"] is briefs[6]["C"]              # the one v6 brief scores every class


def test_load_brief_rejects_wrong_version(tmp_path):
    path = tmp_path / "brief.yaml"
    path.write_text("name: x\nobjective:\n  version: 4\n  tolerances: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        rv.load_brief(path)


# ------------------------------------------------------------------ ranking / analysis


def _rank_row(design: str, j6: float, j7: float) -> dict:
    return {"design_hash": design, "target_key": "90x60_300-8000_f0=600", "class": "A",
            "J_v6": j6, "J_v7": j7, "gate_h": False, "gate_v": False, "gate_di": False,
            "gate_bw8k": False, "gate_load": False, "gate_pass_all_no_throat": False,
            "family": "TEST", "stored_version": None, "shard": 0, "row": 0,
            "v6_load_near": 0.0, "v6_z_smooth": 0.0, "v7_load": 0.0, "v7_flat_cv": 0.0,
            "v7_lfp20_hz": 0.0, "gate_unresolved": "throat"}


def test_better_puts_penalties_last():
    assert rv._better(5.0) < rv._better(1200.0)          # penalty floor is 1e3
    assert rv._better(float("nan"))[0] == 1              # non-finite groups with the penalties
    assert rv._better(5.0)[0] == 0


def test_unique_best_dedupes_and_sorts():
    rows = [
        _rank_row("a", 3.0, 30.0),
        _rank_row("a", 2.0, 31.0),                        # duplicate design: best row wins
        _rank_row("b", 1.0, 29.0),
        _rank_row("p", 1001.0, 0.0),                      # v6 penalty row sorts last under v6
    ]
    u6 = rv.unique_best(rows, 6)
    assert [r["design_hash"] for r in u6] == ["b", "a", "p"]
    assert math.isclose(u6[0]["J_v6"], 1.0)
    u7 = rv.unique_best(rows, 7)
    # Under v7 row "p" is finite (J_v7 = 0.0), so it sorts FIRST there and last under v6.
    assert [r["design_hash"] for r in u7] == ["p", "b", "a"]


def test_class_summary_kendall_tau_and_gates():
    rows = [
        _rank_row("d1", 1.0, 5.0),
        _rank_row("d2", 2.0, 4.0),
        _rank_row("d3", 3.0, 3.0),
        _rank_row("d4", 4.0, 2.0),
        _rank_row("d5", 5.0, 1.0),
    ]
    summary = rv.class_summary(rows)
    block = summary["A"]
    assert block["rows"] == 5
    assert block["unique_designs"] == 5
    assert math.isclose(block["kendall_tau"], -1.0)       # exactly rank-reversed
    assert block["top20_overlap"] == 5                    # 5 unique designs: both top-20 lists are full
    assert block["gates"]["penalty_v6"] == 0
    # no gate flags set on these synthetic rows
    assert block["gates"]["row_pass"]["gate_h"] == 0


def test_class_summary_skips_empty_class():
    summary = rv.class_summary([_rank_row("d1", 1.0, 1.0)])
    assert set(summary) == {"A"}


# ------------------------------------------------------------------ synthetic stored row end-to-end


_NF = 7
FREQS = np.array([250.0, 300.0, 600.0, 1200.0, 2400.0, 4800.0, 8000.0])
#: The repo's real cut grid (2.5 deg steps, -90..+90, exact 0): >= 7 in-coverage samples per
#: plane so the v2 detrended-ripple helper can measure a (here zero) residual.
ANGLES = np.arange(-90.0, 90.1, 2.5)
NB = 8


def _perfect_arrays(z_real: float = 0.9) -> dict:
    n, na = _NF, ANGLES.size
    return {
        "freqs_hz": FREQS.copy(),
        "bw_h_deg": np.full(n, 90.0),
        "bw_v_deg": np.full(n, 60.0),
        "di_db": np.full(n, 8.0),
        "ripple_h_db": np.zeros(n),
        "ripple_v_db": np.zeros(n),
        "on_axis_db": np.full(n, 95.0),
        "z_throat": (z_real + 0.0j) * np.ones(n, dtype=complex),
        "h_angles_deg": ANGLES.copy(),
        "v_angles_deg": ANGLES.copy(),
        "spl_h_db": np.full((n, na), 85.0),
        "spl_v_db": np.full((n, na), 85.0),
        "balloon_dirs": np.tile(np.linspace(-1.0, 1.0, NB).reshape(NB, 1), (1, 3)) / np.sqrt(3.0),
        "spl_balloon_db": np.full((_NF, NB), 85.0),
    }


def _perfect_meta() -> dict:
    return {
        "ok": True,
        "design_hash": "cafe1234",
        "mesh_hash": "mesh1",
        "family": "OSSE",
        "objective": 1.5,
        "n_dof": 3850,
        "objective_version": 6,
        "solve": {"n_dof": 3850, "seconds": 1.0, "backend": "test",
                  "observation": {"distance_m": 2.0}},
        "metrics_scalars": {"di_source": "balloon"},
    }


def _briefs_diag_off() -> dict:
    """The real briefs, with the v7 class briefs' ``diag`` weight set to 0.

    The synthetic balloon (constant SPL on a linear ramp of directions) is not a physically
    meaningful 45/135-degree beamwidth measurement, so the v7 ``diag`` term would charge a
    fixture artefact. Turning that ONE weight off keeps the test about the real v7 brief's
    coverage/loading/flatness maths; the diag term itself is covered by test_objective_v7.py.
    """
    import dataclasses

    base = rv.brief_configs()
    return {6: base[6],
            7: {cls: dataclasses.replace(cfg, weights={**cfg.weights, "diag": 0.0})
                for cls, cfg in base[7].items()}}


def _score(z_real: float = 0.9, briefs: dict | None = None):
    meta = _perfect_meta()
    arrays = _perfect_arrays(z_real)
    parsed = rv.ga.parse_stored_row(rv._row_to_gate_row(meta, arrays), "test")
    assert parsed is not None
    metrics, resp = rv.build_scoring_inputs(meta, arrays, parsed)
    target = _target()
    cls = rv.classify_target(target)
    scored = rv.score_versions(metrics, resp, target, briefs or _briefs_diag_off(), cls)
    gates = rv.gate_results(parsed, target)
    return parsed, metrics, resp, target, cls, scored, gates


def test_parse_and_rebuild_of_synthetic_stored_row():
    parsed, metrics, resp = _score()[:3]
    assert parsed["freqs"].size == _NF
    assert parsed["z_real"] is not None and parsed["z_real"][0] == pytest.approx(0.9)
    assert np.isfinite(metrics.on_axis_db).all()
    assert resp is not None
    assert resp.axis_index == 36                         # the 0-degree sample of the real grid


def test_score_versions_perfect_row_is_finite_and_small():
    parsed, metrics, resp, target, cls, scored, gates = _score()
    assert cls == "B"
    j6, t6 = scored[6]
    j7, t7 = scored[7]
    assert math.isfinite(j6) and j6 < rv.PENALTY_FLOOR
    assert math.isfinite(j7) and j7 < rv.PENALTY_FLOOR
    assert j7 == pytest.approx(0.0, abs=0.5)             # every scored metric exactly on target
    assert t7["lfp20_hz"] == pytest.approx(250.0)         # resolved low at the grid start
    # The v7 gate must agree with the v7 objective: a loaded constant row passes the load gate.
    assert gates["load"] is True
    assert gates["h"] is True and gates["v"] is True and gates["di"] is True
    assert gates["bw8k"] is True
    assert gates["pass_all_no_throat"] is True
    assert gates["throat"] is None


def test_score_versions_unloaded_row_is_charged_and_gate_fails():
    parsed, metrics, resp, target, cls, scored, gates = _score(z_real=0.1)
    j7, t7 = scored[7]
    assert math.isfinite(j7) and j7 > 10.0               # unmeasurable LFP20 -> NAN_TERM_FILL-weighted
    assert t7["lfp20_hz"] == pytest.approx(30.0)          # NAN_TERM_FILL marks the unmeasurable LFP20
    assert gates["load"] is False
    assert gates["pass_all_no_throat"] is False


def test_build_scoring_inputs_without_polars():
    meta = _perfect_meta()
    arrays = _perfect_arrays()
    for key in ("h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db"):
        arrays.pop(key)
    parsed = rv.ga.parse_stored_row(rv._row_to_gate_row(meta, arrays), "test")
    metrics, resp = rv.build_scoring_inputs(meta, arrays, parsed)
    assert resp is None
    scored = rv.score_versions(metrics, resp, _target(), rv.brief_configs(), "B")
    for j, _t in scored.values():                         # v2 helpers degrade, never crash
        assert math.isfinite(float(j))


# ------------------------------------------------------------------ CSV writer


def test_write_csv_roundtrip(tmp_path):
    rows = [_rank_row("d1", 1.5, 2.5), _rank_row("d2", 0.5, 3.5)]
    path = tmp_path / "out.csv"
    rv.write_csv(path, rows)
    with path.open(newline="", encoding="utf-8") as fh:
        got = list(csv.DictReader(fh))
    assert len(got) == 2
    assert float(got[1]["J_v6"]) == 0.5
    assert set(got[0]) >= set(rv.CSV_FIELDS)


# ------------------------------------------------------------------ summary JSON writer


def test_write_summary_json_writes_nan_as_null(tmp_path):
    path = tmp_path / "summary.json"
    rv.write_summary_json(path, {"classes": {"A": {"kendall_tau": float("nan")}}})
    assert "null" in path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ driver_check (report-only)


def test_driver_check_flags_missing_mmd(tmp_path):
    y1 = tmp_path / "nomd.yaml"
    y1.write_text(
        "kind: cone\nname: nomd\nre_ohm: 5.5\nle_mh: 0.39\nbl_tm: 16.9\nsd_cm2: 346\n"
        "mms_g: 32\nfs_hz: 65\nqms: 5.6\nxmax_mm: 4\ncms_mm_per_n: 1.0\n"
        "cutout_mm: 0\ndepth_mm: 1\np_aes_w: 350\nsource: https://example.com\n"
        "sens_db_2v83: 100.0\n", encoding="utf-8")
    y2 = tmp_path / "withmd.yaml"
    y2.write_text(
        "kind: cone\nname: withmd\nre_ohm: 5.5\nle_mh: 0.39\nbl_tm: 16.9\nsd_cm2: 346\n"
        "mmd_g: 30\nfs_hz: 65\nqms: 5.6\nxmax_mm: 4\ncms_mm_per_n: 1.0\n"
        "cutout_mm: 0\ndepth_mm: 1\np_aes_w: 350\nsource: https://example.com\n"
        "sens_db_2v83: 100.0\n", encoding="utf-8")
    rows = dc.collect(tmp_path)
    by_file = {r["file"]: r for r in rows}
    assert "Mms only" in by_file["nomd.yaml"]["mass_status"]
    assert by_file["withmd.yaml"]["mass_ok"] is True
    for r in rows:
        assert r["source_url"] == "yes"
        assert r["has_sensitivity"] is True


def test_driver_check_readiness_on_real_files_counts_fields():
    rows = dc.collect()
    real = [r for r in rows if not r["is_template"]]
    assert len(real) >= 10
    # report-only audit: every real file must resolve to a documented readiness row
    for r in real:
        assert r["mass_status"] and r["kind"]
