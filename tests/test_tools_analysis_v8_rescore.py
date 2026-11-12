"""Offline tests for tools/analysis/v8_rescore.py (day group G).

NO GPU, NO solver, NO dataset writes: the pipeline runs against a synthetic dataset directory
(the same shard-*.jsonl + shard-NNNN/rec-NNNN.npz shape the real records carry) in ``tmp_path``,
and the real class-matched v4/v6/v7 briefs are loaded from the repo. Contracts:

* calibration: per class, tolerance = median raw-unit value over the top decile
  (``max(3, ceil(n/10))``) of the rows ranked by the class-matched v4 J; a class with no
  rankable rows calibrates to nothing (degrade, never fake);
* the tool walks the dataset read-only and writes JSON+MD ONLY under ``--out``;
* the pair analysis reports Kendall tau (over shared (design, target) keys below the penalty
  floor) and top-20 overlap for v8 vs v4/v6/v7, and v8 hard-refusal gate counts;
* determinism: two runs on the same inputs write byte-identical JSON.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys

import numpy as np
import pytest

from conftest import REPO

_TOOL = REPO / "tools" / "analysis" / "v8_rescore.py"


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


v8t = _load_tool("v8_rescore_tool", _TOOL)


# ------------------------------------------------------------------ calibration (pure rows)

def _cal_row(design: str, j4: float, cov: float, rip: float = 0.5) -> dict:
    row = {"design_hash": design, "target_key": "90x60_300-8000_f0=850", "class": "A",
           "J_v4": j4, "J_v6": j4 + 1.0, "J_v7": j4 + 2.0,
           "v8_gate_failed": False, "v8_gate_reason": None}
    for k, v in (("cov", cov), ("rip", rip), ("di", 1.0), ("dislope", 1.0), ("flat", 0.5),
                 ("distd", 0.5), ("diag", 12.0), ("flat_cv", 0.7)):
        row[f"v8raw_{k}"] = v
    return row


def test_calibrate_takes_the_median_of_the_top_decile_ranked_by_v4():
    rows = [_cal_row(f"d{i}", j4=float(i), cov=float(i) * 2.0) for i in range(12)]
    rows.append(_cal_row("penalty", 2000.0, 99.0))          # refusal/penalty: never ranked
    cal = v8t.calibrate(rows, "A")
    # n_top = max(3, ceil(12/10)) = 3 rows: the BEST J_v4 values 2.0, 1.0, 0.0 -> cov 4, 2, 0.
    assert cal["n_top"] == 3 and cal["n_valid"] == 12
    assert cal["tolerances"]["cov"] == pytest.approx(2.0)
    assert cal["tolerances"]["rip"] == pytest.approx(0.5)
    assert all(math.isfinite(cal["tolerances"][k]) and cal["tolerances"][k] > 0.0
               for k in v8t.V8_WEIGHTED_KEYS)


def test_calibrate_skips_an_empty_class_and_never_fakes():
    assert v8t.calibrate([], "A") is None
    assert v8t.calibrate_all([]) == {}                    # class B/C have no rows


# ------------------------------------------------------------------ synthetic dataset rows

_NF = 8
FREQS = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 7000.0, 8000.0])
ANGLES = np.arange(-90.0, 90.1, 2.5)
NB = 500


def _sphere_dirs(n: int = NB) -> np.ndarray:
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    phi = math.pi * (1 + 5 ** 0.5) * i
    r = np.sqrt(1 - z * z)
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


_REF_DI = 9.0
_DIRS = _sphere_dirs()


def _balloon_db(width_deg: float) -> np.ndarray:
    """A round beam whose -6.0206 dB half-angle is width/2 (relative to the on-axis level)."""
    th = np.degrees(np.arccos(np.clip(_DIRS[:, 2], -1, 1)))
    return -6.0206 * (th / (width_deg / 2.0)) ** 2


def _arrays(bw_off: float, di_off: float, slope: float, pinch: float, z_real: float,
            on_axis_bump: float, wiggle: float = 0.6) -> dict:
    n = _NF
    di = _REF_DI + di_off + slope * np.log10(FREQS / 1000.0)
    on_axis = 0.0 + on_axis_bump * (np.log2(FREQS) - float(np.mean(np.log2(FREQS)))) ** 2
    taper = -6.0206 * (np.radians(ANGLES) / np.radians(45.0)) ** 2
    ripple = wiggle * np.sin(7.0 * np.radians(ANGLES))
    spl_h = on_axis[:, None] + taper[None, :] + ripple[None, :]
    return {
        "freqs_hz": FREQS.copy(),
        "bw_h_deg": np.full(n, 90.0 + bw_off),
        "bw_v_deg": np.full(n, 60.0 + bw_off),
        "di_db": di,
        "ripple_h_db": np.full(n, 0.5),
        "ripple_v_db": np.zeros(n),
        "on_axis_db": on_axis,
        "z_throat": (z_real + 0.0j) * np.ones(n, dtype=complex),
        "h_angles_deg": ANGLES.copy(),
        "v_angles_deg": ANGLES.copy(),
        "spl_h_db": spl_h,
        "spl_v_db": spl_h,
        "balloon_dirs": _DIRS.copy(),
        "spl_balloon_db": np.tile(_balloon_db(60.0 - pinch), (n, 1)),
    }


_TARGETS = {
    "A": dict(coverage_h_deg=90.0, coverage_v_deg=60.0, band_lo_hz=300.0, band_hi_hz=8000.0,
              di_target_db=None, di_slope_target=0.0, z_min=0.0, f0_hz=850.0,
              driver_exit_radius_mm=18.0),
    "B": dict(coverage_h_deg=90.0, coverage_v_deg=60.0, band_lo_hz=300.0, band_hi_hz=8000.0,
              di_target_db=None, di_slope_target=0.0, z_min=0.7, f0_hz=600.0,
              driver_exit_radius_mm=18.0),
    "C": dict(coverage_h_deg=90.0, coverage_v_deg=90.0, band_lo_hz=300.0, band_hi_hz=8000.0,
              di_target_db=None, di_slope_target=0.0, z_min=0.0, f0_hz=400.0,
              driver_exit_radius_mm=18.0),
}


def _meta(target: dict, design: str, j: float) -> dict:
    return {
        "ok": True,
        "design_hash": design,
        "mesh_hash": "m" + design,
        "family": "OSSE",
        "objective": j,
        "objective_version": 4,
        "solve": {"n_dof": 3850, "seconds": 1.0, "backend": "test",
                  "observation": {"distance_m": 2.0}},
        "metrics_scalars": {"di_source": "balloon", "f11_hz": 5584.0},
        "target": target,
    }


#: (class, design, bw_off, di_off, slope, pinch, z, on_axis_bump, stored_J)
_SPEC = [
    ("A", "aa1", 3.0, 1.0, 1.5, 0.0, 0.9, 0.20, 9.0),
    ("A", "aa2", 8.0, 2.0, 2.0, 0.0, 0.8, 0.40, 8.0),
    ("A", "aa3", 5.0, 1.5, 1.0, 14.0, 0.7, 0.10, 7.0),
    ("A", "aa4", 6.0, 0.5, 1.8, 4.0, 0.6, 0.30, 6.0),
    ("B", "bb1", 2.0, 1.0, 1.0, 0.0, 0.9, 0.10, 5.0),
    ("B", "bb2", 7.0, 2.5, 2.2, 6.0, 0.8, 0.25, 4.0),
    ("B", "bb3", 4.0, 0.2, 0.5, 2.0, 0.15, 0.05, 3.0),      # unloaded z: v8 refuses this row
    ("C", "cc1", 3.5, 1.2, 1.4, 0.0, 0.9, 0.15, 2.0),
    ("C", "cc2", 9.0, 2.2, 2.4, 8.0, 0.85, 0.35, 1.0),
    ("C", "cc3", 5.5, 0.8, 1.1, 3.0, 0.75, 0.05, 0.5),
]


def _write_dataset(root) -> None:
    shard = root / "shard-0000"
    shard.mkdir(parents=True)
    lines = []
    for i, (cls, design, bw_off, di_off, slope, pinch, z, bump, j) in enumerate(_SPEC):
        arrays = _arrays(bw_off, di_off, slope, pinch, z, bump)
        meta = _meta(_TARGETS[cls], design, j)
        lines.append(json.dumps(meta))
        np.savez(shard / f"rec-{i:04d}.npz", **arrays)
    (root / "shard-0000.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ end-to-end

def test_full_run_calibrates_scores_and_writes_json_md(tmp_path):
    ds = tmp_path / "dataset"
    _write_dataset(ds)
    out = tmp_path / "out"
    rc = v8t.main(["--dataset", str(ds), "--out", str(out)])
    assert rc == 0
    summary = json.loads((out / "v8_rescore.json").read_text(encoding="utf-8"))
    assert summary["counters"]["scored"] == len(_SPEC)
    assert summary["counters"]["rows_seen"] == len(_SPEC)
    assert set(summary["calibration"]) == {"A", "B", "C"}
    for cls, cal in summary["calibration"].items():
        assert set(cal["tolerances"]) == set(v8t.V8_WEIGHTED_KEYS)
        assert all(v > 0.0 for v in cal["tolerances"].values())
        assert cal["n_top"] == max(3, math.ceil(cal["n_valid"] / 10))
    for cls in ("A", "B", "C"):
        block = summary["classes"][cls]
        assert block["rows"] == sum(1 for s in _SPEC if s[0] == cls)
        assert block["unique_designs"] == sum(1 for s in _SPEC if s[0] == cls)
        for base in (4, 6, 7):
            p = block["pairs"][str(base)]
            assert p["n_shared"] == sum(1 for s in _SPEC if s[0] == cls)
            assert -1.0 <= p["kendall_tau"] <= 1.0
            assert 0 <= p["top20_overlap"] <= block["rows"]
    # the unloaded class-B row is refused by the v8 loading gate
    b = summary["classes"]["B"]["v8_gate_refusals"]
    assert b["rows"] == 1 and b["by_reason"]
    md = (out / "v8_rescore.md").read_text(encoding="utf-8")
    assert "owner sign-off" in md and "Kendall" in md
    # nothing was written next to the dataset
    assert sorted(p.name for p in ds.iterdir()) == ["shard-0000", "shard-0000.jsonl"]


def test_full_run_is_deterministic(tmp_path):
    ds = tmp_path / "dataset"
    _write_dataset(ds)
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    v8t.main(["--dataset", str(ds), "--out", str(out1)])
    v8t.main(["--dataset", str(ds), "--out", str(out2)])
    a = (out1 / "v8_rescore.json").read_bytes()
    b = (out2 / "v8_rescore.json").read_bytes()
    assert a == b


def test_real_briefs_load_with_their_versions():
    briefs = v8t.brief_configs()
    assert set(briefs) == {4, 6, 7}
    for cls in ("A", "B", "C"):
        assert briefs[4][cls].version == 4
        assert briefs[6][cls].version == 6
        assert briefs[7][cls].version == 7
        # the class cov facts come from the brief, and v8 inherits them
        vp = v8t.v8_params_for_class(cls, briefs[4][cls])
        assert vp.cov_narrow_ratio == briefs[4][cls].params.cov_narrow_ratio
        assert vp.cov_below_f0 == briefs[4][cls].params.cov_below_f0


def test_missing_dataset_is_an_error(tmp_path):
    rc = v8t.main(["--dataset", str(tmp_path / "nope"), "--out", str(tmp_path / "out")])
    assert rc == 2
