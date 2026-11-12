"""Shared synthetic-run fixtures for the `tests/test_tools_analysis_*.py` files, plus
unit tests for `tools/analysis/_common.py` (the helpers every Group A tool builds on).

Nothing here touches real data: run dirs are built inside ``tmp_path`` with small
``search.ndjson`` / ``config.yaml`` / ``run.json`` fixtures shaped exactly like the
repo writes them (``hornlab_search/search/evaluate.py::evaluation_to_row``,
``hornlab_search/search/cma.py``'s run.json, ``hornlab_search/config.py`` bounds).

The tool test modules import THIS module for the fixtures and the module loader (the
tools import each other through ``tools/analysis`` being on ``sys.path`` — ``tools/`` is
not a package).
"""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "tools" / "analysis"
TESTS = Path(__file__).resolve().parent

if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

#: the interpreter the tests run under (locally the venv's python via PY; in CI the
#: job's python — never a hard-coded machine path, so the tests also run on Linux CI)
PY = Path(sys.executable)


def load_tool(name: str) -> Any:
    """Import a tool module by file path, exactly the way report_day.py does."""
    path = ANALYSIS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"analysis_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# A realistic OSSE/v4 config snapshot (the fields the analysis tools read: name,
# family, weights, objective.tolerances, bounds). Knob names are real knob names.
BASE_CONFIG = {
    "name": "native__ath_core_v4",
    "description": "synthetic analysis-test config",
    "family": "OSSE",
    "weights": {"cov": 1.0, "rip": 1.0, "di": 1.0, "dislope": 1.0, "flat": 1.0,
                "load": 0.0, "distd": 1.0, "diag": 0.0},
    "objective": {
        "version": 4,
        "tolerances": {"cov": 0.05, "rip": 0.5, "di": 2.0, "dislope": 1.0,
                       "flat": 2.0, "load": 1.0, "distd": 3.0, "diag": 3.0},
    },
    "bounds": {
        "a_deg": {"lo": 10.0, "hi": 60.0},
        "a0_deg": {"lo": 0.0, "hi": 30.0},
        "n": {"lo": 1.0, "hi": 8.0},
        "t0_mm": {"lo": 20.0, "hi": 60.0},
        "L_mm": {"lo": 140.0, "hi": 420.0, "search": False},
    },
}


def kn(  # noqa: N802 - short factory name used a lot in the tests
    i: int, *, a_lo: float = 10.0, a_hi: float = 60.0, n_lo: float = 1.0,
    n_hi: float = 8.0, t_lo: float = 20.0, t_hi: float = 60.0
) -> dict:
    """Deterministic knob vector i (i >= 0) inside BASE_CONFIG's searched bounds."""
    k = float(i)
    return {"a_deg": a_lo + (a_hi - a_lo) * ((k * 7) % 100) / 100.0,
            "a0_deg": (k * 3) % 30.0,
            "n": n_lo + (n_hi - n_lo) * ((k * 11) % 100) / 100.0,
            "t0_mm": t_lo + (t_hi - t_lo) * ((k * 13) % 100) / 100.0}


def v4_terms(raw: dict, weights: dict, tolerances: dict) -> dict:
    """A v4 ``terms`` row dict from RAW term values (t = raw/tol; total = sum w*t);
    same contract as ``hornlab_search/objective/scalar_v4.py`` lines 253-260."""
    t = {k_: float(raw[k_]) / float(tolerances[k_]) for k_ in tolerances}
    t["total"] = float(sum(weights.get(k_, 0.0) * t[k_] for k_ in tolerances))
    t.update({"penalty": 0.0, "n_nan": 0, "n_in_band": 6, "di_estimated": False})
    return t


def make_row(i: int, objective: float, *, ok: bool = True, cached: bool = False,
             kind: str = "ok", error: str | None = None, params: dict | None = None,
             design_hash: str | None = None, mode: str = "screen", version: int = 4,
             family: str = "OSSE", seconds: float | None = 2.0,
             terms: dict | None = None, n: int | None = None,
             created: str = "2026-11-12T10:00:00Z") -> dict:
    """One ``search.ndjson`` row (subset of ``evaluation_to_row``'s schema the tools read)."""
    return {
        "n": n if n is not None else i + 1,
        "mode": mode,
        "key": f"{design_hash or f'dh{i:04d}'}-m{i}-s{i}",
        "design_hash": design_hash or f"dh{i:04d}",
        "mesh_hash": f"m{i:04d}", "solve_hash": f"s{i:04d}",
        "family": family, "params": params if params is not None else kn(i),
        "objective_version": version, "objective": objective,
        "terms": terms if terms is not None else {},
        "ok": ok, "error": error, "kind": kind, "cached": cached,
        "seconds": {"total": seconds} if seconds is not None else {},
        "metrics": {}, "created_utc": created,
    }


def write_run(rows: list[dict], tmp_path: Path, name: str = "run", *,
              config: dict | None = None, family: str = "OSSE", seed: int = 1030,
              extra_run_json: dict | None = None) -> Path:
    """A run dir: ``search.ndjson`` + ``config.yaml`` + ``run.json`` (+ optional extras)."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "search.ndjson").write_text(
        "".join(json.dumps(r, allow_nan=False, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8")
    cfg = dict(BASE_CONFIG) if config is None else config
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    run_json = {"run_id": name, "config_name": cfg.get("name"), "family": family,
                "mode": rows[0]["mode"] if rows else "screen",
                "cma_seed": seed, "config": cfg, "status": "finished",
                # real runs record library pins; a stable default keeps synthetic
                # compatibility checks meaningful (override in tests as needed)
                "lib_shas": {"hornlab_search": "test-sha",
                             "hornlab_beat_bem": "test-sha",
                             "hornlab_mesher": "test-sha",
                             "hornlab_plots": "test-sha",
                             "hornlab_bempp_bem": "test-sha"}}
    run_json.update(extra_run_json or {})
    (d / "run.json").write_text(json.dumps(run_json, indent=1, allow_nan=False),
                                encoding="utf-8")
    return d


def run_cli(tool: str, args: list[str], tmp_path: Path, out: str = "out"):
    """Run a tool's CLI in a subprocess (the documented usage), return CompletedProcess.
    The output folder is ``tmp_path / out``."""
    return subprocess.run(
        [str(PY), str(ANALYSIS / f"{tool}.py"), *args, "--out", str(tmp_path / out)],
        capture_output=True, text=True, cwd=str(REPO), timeout=300)


def run_json_payload(out_dir: Path, tool: str) -> dict:
    """Parsed ``<tool>.json`` written by a tool into ``out_dir``."""
    return json.loads((Path(out_dir) / f"{tool}.json").read_text(encoding="utf-8"))


# =====================================================================  _common tests

cm = load_tool("_common")


# --------------------------------------------------------------------- beats_rule

def test_beats_rule_matches_schema():
    # rule: medians differ by more than BOTH spreads (strictly)
    assert cm.beats_rule(12.0, 1.9, 14.0, 1.0, 6) == "a-beats-b"   # diff 2 > 1.9 and > 1.0
    assert cm.beats_rule(14.0, 1.9, 12.0, 1.0, 6) == "b-beats-a"
    assert cm.beats_rule(12.0, 2.0, 14.0, 1.0, 6) == "no-verdict"  # diff == spread_a: not more
    assert cm.beats_rule(12.0, 2.0, 13.9, 1.0, 6) == "no-verdict"  # diff 1.9 > spread_b only
    assert cm.beats_rule(12.0, 1.9, 14.0, 1.0, 4) == "indicative"  # 3-4 seeds
    assert cm.beats_rule(12.0, 1.9, 14.0, 1.0, 2) == "indicative"  # rule holds, <5 (schema)
    assert cm.beats_rule(12.0, 1.9, 12.9, 0.5, 10) == "no-verdict"


# --------------------------------------------------------------------- evals_to_within

def _curve(bests: list[float]) -> list[dict]:
    return [{"n": i + 1, "best": b, "wall_s": 2.0 * (i + 1)} for i, b in enumerate(bests)]


def test_evals_to_within_is_evals_until_best_is_within_target():
    # bests decrease monotonically to 11.0; 1% band of 11.0 is <= 11.11, 5% <= 11.55
    curve = _curve([100.0, 50.0, 25.0, 11.5, 11.0])
    assert cm.evals_to_within(curve, 11.0, 0.01) == 5   # only the last point is <= 11.11
    assert cm.evals_to_within(curve, 11.0, 0.05) == 4   # 11.5 <= 11.55
    assert cm.evals_to_within([], 11.0, 0.01) is None


def test_last20_improvement_flag_and_pct():
    # 20 evals; new minimum 10.8 appears at n=16 (inside the last 20% = n >= 16)
    head = [30.0, 25.0, 20.0, 18.0, 16.0, 14.0, 13.0, 12.0, 11.5, 11.2]
    tail = [11.1, 11.05, 11.03, 11.02, 11.0] + [10.8] + [10.8, 10.8, 10.8, 10.8]
    flag, pct = cm.last20_improvement(_curve(head + tail))
    assert flag is True
    assert pct == pytest.approx((11.0 - 10.8) / 10.8 * 100.0)
    # flat tail: minimum reached at n=15, no improvement inside the last 20%
    tail2 = [11.1, 11.05, 11.03, 11.02, 11.0, 11.0, 11.0, 11.0, 11.0, 11.0]
    flag2, pct2 = cm.last20_improvement(_curve(head + tail2))
    assert flag2 is False
    assert pct2 == pytest.approx(0.0)
    assert cm.last20_improvement(_curve([10.0, 9.0])) == (False, None)  # < 10 evals


# --------------------------------------------------------------------- refusal_windows

def test_refusal_windows_by_kind():
    # windows cover NON-CACHED rows only (schema: replays are not new evals)
    rows = [make_row(0, 100.0),
            make_row(1, 50.0),
            make_row(2, 1000.0, ok=False, kind="invalid_geometry", error="geom"),
            make_row(3, 50.0, cached=True),
            make_row(4, 20.0, ok=False, kind="invalid_geometry", error="geom")]
    wins = cm.refusal_windows(rows, w=50)
    assert len(wins) == 1
    assert wins[0]["w"] == [1, 4]
    assert wins[0]["rate"] == pytest.approx(2 / 4)
    assert wins[0]["kinds"] == {"invalid_geometry": 2}


def test_refusal_windows_last_window_may_be_short():
    rows = [make_row(i, 20.0 if i % 4 == 0 else 1000.0, ok=(i % 4 == 0),
                     kind=("invalid_geometry" if i % 4 != 0 else "ok"))
            for i in range(103)]
    wins = cm.refusal_windows(rows, w=50)
    assert [w["w"] for w in wins] == [[1, 50], [51, 100], [101, 103]]
    assert wins[2]["rate"] == pytest.approx(2 / 3)


# --------------------------------------------------------------------- spearman/ranks

def test_spearman_perfect_monotone():
    x = list(range(10))
    assert cm.spearman(x, [3.0 * v + 1 for v in x]) == pytest.approx(1.0)
    assert cm.spearman(x, [-2.0 * v + 5 for v in x]) == pytest.approx(-1.0)
    assert cm.spearman(x, [10.0 - v for v in x]) == pytest.approx(-1.0)
    with_ties = [1.0, 1.0, 2.0, 3.0]
    y = [5.0, 6.0, 7.0, 8.0]
    rho = cm.spearman(with_ties, y)
    assert rho is not None and -1.0 <= rho <= 1.0


def test_spearman_needs_three_rows():
    assert cm.spearman([1.0, 2.0], [1.0, 2.0]) is None
    # two finite pairs survive the nan filter -> still below the 3-row floor
    assert cm.spearman([1.0, np.nan, 3.0], [1.0, 2.0, 3.0]) is None
    assert cm.spearman([1.0, np.nan, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)


def test_spearman_fallback_formula_matches_scipy_when_scipy_present():
    """Both code paths (scipy and the hand-rolled ranks) must agree with scipy itself."""
    rng = np.random.default_rng(1)
    x = rng.normal(size=200)
    y = 2.0 * x + rng.normal(size=200)
    rho = cm.spearman(x, y)
    assert rho is not None and rho > 0.8
    import scipy.stats as sps
    rho_scipy = float(sps.spearmanr(x, y)[0])  # type: ignore[call-overload, Misc] - namedtuple
    assert rho == pytest.approx(rho_scipy)
    # fallback formula, bypassing scipy
    xv, yv = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    rx, ry = cm._ranks(xv), cm._ranks(yv)
    dx, dy = rx - rx.mean(), ry - ry.mean()
    assert float(dx @ dy) / math.sqrt(float(dx @ dx) * float(dy @ dy)) == pytest.approx(rho)


# --------------------------------------------------------------------- fixture contract

def test_params_flat_handles_grid_kernel_and_filters_non_numeric():
    row = {"params": {"grid": {"knobs": {"a_deg": 25.0, "name": "x", "flag": True,
                                         "n": float("nan")}}}}
    assert cm.params_flat(row) == {"a_deg": 25.0}


def test_bounds_of_skips_non_search_knobs():
    assert cm.bounds_of(BASE_CONFIG)["a_deg"] == (10.0, 60.0)
    assert "L_mm" not in cm.bounds_of(BASE_CONFIG)


def test_top_decile_size_floor_and_ordering():
    rows = [make_row(i, 100.0 - i) for i in range(25)]
    top = cm.top_decile(rows)
    assert top is not None and len(top) == 3  # max(3, ceil(25/10))... ceil(2.5)=3
    assert [r["objective"] for r in top] == [76.0, 77.0, 78.0]
    few = [make_row(i, 100.0 - i) for i in range(2)]
    assert cm.top_decile(few) is None


def test_bootstrap_ci_fixed_seed_reproducible():
    vals = [10.0, 11.0, 12.0, 13.0, 14.0]
    ci = cm.bootstrap_ci(vals, n_boot=500, seed=0)
    assert ci == cm.bootstrap_ci(vals, n_boot=500, seed=0)
    assert ci is not None and ci[0] <= 12.0 <= ci[1]
    assert cm.bootstrap_ci([1.0]) is None


# --------------------------------------------------------------------- jsonable/write_report

def test_jsonable_maps_nonfinite_to_null_and_numpy_to_python():
    out = cm.jsonable({"a": np.float64(1.5), "b": np.float64(math.inf),
                       "c": np.float64(math.nan), "d": [np.int64(3), np.bool_(True)],
                       "e": {"f": None}, "g": (1, 2)})
    assert out == {"a": 1.5, "b": None, "c": None, "d": [3, True], "e": {"f": None},
                   "g": [1, 2]}


def test_write_report_sanitizes_json_and_writes_md(tmp_path):
    payload = {"runs": [{"final_best": math.inf, "n_valid": 3}]}
    written = cm.write_report(tmp_path, "t", payload, "# md body")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t.json", "t.md"]
    doc = run_json_payload(tmp_path, "t")
    assert doc["tool"] == "t" and "generated_utc" in doc
    assert doc["runs"][0]["final_best"] is None
    assert (tmp_path / "t.md").read_text(encoding="utf-8") == "# md body"
    assert set(written) == {"json", "md"}
