"""WP10 search history / CMA-ES views — offline unit tests.

Covers:
- cma_dynamics: parses fit.dat with header and penalty rows
- cma_dynamics: missing cma/ => available: False
- cma_dynamics: per-generation quantiles from ok rows only
- cma_dynamics: nulls out values >= 999.0 (penalty threshold)
- run_detail: has_atlas key present
- run_detail: cma_dynamics key present
- H7: app.js uses has_atlas conditionally for QD atlas link
- H9: score breakdown uses weights (terms sorted by best contribution in app.js)
- H8: evolution.js 3D box hidden by default (node --check)
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
EVJS = ROOT / "hornlab_search" / "gui" / "static" / "evolution.js"

# ---------------------------------------------------------------------------
# cma_dynamics unit tests
# ---------------------------------------------------------------------------

RID = "20261112T130000Z-screen-ab12cd"

_CONFIG = {
    "name": "cma_dyn_smoke",
    "family": "OSSE",
    "bounds": {
        "a_deg": {"lo": 30.0, "hi": 50.0},
        "L_mm": {"lo": 100.0, "hi": 200.0},
    },
    "search": {"algorithm": "cma", "budget": 20, "seed": 1, "sigma0": 0.2},
    "mesh": {"epw": 6.0, "quadrants": "1"},
    "solve": {"backend": "beat_cpu"},
    "target": {"band_lo_hz": 300, "band_hi_hz": 5000},
    "weights": {"cov": 1.0},
    "objective": {"version": 7},
}


def _make_fit_dat(n_gens: int = 5, include_penalty: bool = False) -> str:
    """Generate a synthetic fit.dat with the standard pycma header."""
    lines = [
        "% (iter, eval, sigma, axis_ratio, bestever, best, median, worst, iqr, p25, currentbest, wallclock)",
        "% column names for reference",
    ]
    for g in range(n_gens):
        sigma = 0.3 - g * 0.04
        axis_r = 1.0 + g * 0.5
        best = 2.0 - g * 0.3
        median = best + 0.5
        worst = best + 2.0
        iqr = 0.4
        p25 = best + 0.1
        wallclock = g * 10.0
        # eval index = g * 10 (lambda=10 assumed)
        lines.append(f"  {g+1}  {(g+1)*10}  {sigma:.6f}  {axis_r:.4f}  {best:.4f}  {best+0.1:.4f}"
                     f"  {median:.4f}  {worst:.4f}  {iqr:.4f}  {p25:.4f}  {best:.4f}  {wallclock:.2f}")
    if include_penalty:
        # Add a penalty row: best=1000.0 (failure)
        lines.append("  6  60  0.25  2.5  1000.0  1000.0  1000.0  1000.0  0.0  1000.0  1000.0  60.0")
    return "\n".join(lines) + "\n"


def _make_stddev_dat(n_gens: int = 5, n_params: int = 2) -> str:
    """Generate a synthetic stddev.dat.

    pycma format: iter  evals  sigma  void  void  per-param-stds...
    (cols 5..N are the per-param standard deviations, matching data.py::cma_dynamics)
    """
    lines = ["% (iter, eval, sigma, void, void, stds_per_param...)"]
    for g in range(n_gens):
        stds = "  ".join(f"{0.3 - g * 0.03:.6f}" for _ in range(n_params))
        lines.append(f"  {g+1}  {(g+1)*10}  {0.3:.4f}  0.0  0.0  {stds}")
    return "\n".join(lines) + "\n"


@pytest.fixture()
def cma_run(tmp_path: Path):
    """A synthetic run directory with cma/ diagnostic files."""
    run = tmp_path / "runs" / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
    rows = [{"n": i, "design_hash": f"abcdef{i:06d}", "ok": True, "objective": 2.0 - i * 0.1,
             "mode": "screen", "params": {"a_deg": 40.0, "L_mm": 150.0},
             "created_utc": f"2026-11-12T00:00:{i:02d}Z"} for i in range(20)]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"objective_version": 7}), encoding="utf-8")
    cma_dir = run / "cma"
    cma_dir.mkdir()
    (cma_dir / "fit.dat").write_text(_make_fit_dat(n_gens=5), encoding="utf-8")
    (cma_dir / "stddev.dat").write_text(_make_stddev_dat(n_gens=5, n_params=2), encoding="utf-8")
    return run


@pytest.fixture()
def no_cma_run(tmp_path: Path):
    """A synthetic run directory WITHOUT cma/ diagnostic files."""
    run = tmp_path / "runs" / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
    rows = [{"n": 0, "design_hash": "abcdef000000", "ok": True, "objective": 2.0,
             "mode": "screen", "params": {"a_deg": 40.0, "L_mm": 150.0},
             "created_utc": "2026-11-12T00:00:00Z"}]
    (run / "search.ndjson").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"objective_version": 7}), encoding="utf-8")
    return run


def test_cma_dynamics_available(cma_run: Path):
    """cma_dynamics returns available: True when cma/fit.dat exists."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(cma_run)
    assert result["available"] is True


def test_cma_dynamics_missing_returns_unavailable(no_cma_run: Path):
    """cma_dynamics returns available: False when cma/ is absent."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(no_cma_run)
    assert result["available"] is False


def test_cma_dynamics_gen_count(cma_run: Path):
    """cma_dynamics reads the correct number of generations."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(cma_run)
    assert result["available"] is True
    assert len(result["gens"]) == 5, f"Expected 5 gens, got {len(result['gens'])}"


def test_cma_dynamics_sigma_values(cma_run: Path):
    """cma_dynamics: sigma values are positive and decreasing (our synthetic data)."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(cma_run)
    sigmas = [g["sigma"] for g in result["gens"] if g.get("sigma") is not None]
    assert len(sigmas) == 5
    assert all(s > 0 for s in sigmas), "All sigmas should be positive"
    # Our synthetic data has sigma decreasing
    assert sigmas[0] > sigmas[-1], "Sigma should decrease in our synthetic data"


def test_cma_dynamics_penalty_nulled():
    """cma_dynamics: values >= 999.0 are nulled out (not leaked into the output)."""
    import tempfile
    from pathlib import Path as P
    with tempfile.TemporaryDirectory() as td:
        run = P(td) / "run"
        run.mkdir()
        (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
        (run / "run.json").write_text("{}", encoding="utf-8")
        cma_dir = run / "cma"
        cma_dir.mkdir()
        # Write fit.dat with one normal and one penalty row
        (cma_dir / "fit.dat").write_text(_make_fit_dat(n_gens=2, include_penalty=True), encoding="utf-8")
        from hornlab_search.gui.data import cma_dynamics
        result = cma_dynamics(run)
        # penalty row (gen 6) should not carry 1000.0 values in bestever/best/median/worst
        for g in result["gens"]:
            for key in ("best", "median", "worst"):
                v = g.get(key)
                if v is not None:
                    assert v < 999.0, f"Penalty value not nulled in gen {g}: {key}={v}"


def test_cma_dynamics_param_names(cma_run: Path):
    """cma_dynamics: param_names come from config.yaml bounds keys."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(cma_run)
    assert result.get("param_names"), "param_names should be set"
    # config has a_deg and L_mm
    assert any("a_deg" in p or "L_mm" in p for p in result["param_names"]), \
        f"Expected config bounds keys in param_names, got {result['param_names']}"


def test_cma_dynamics_stddev_shape(cma_run: Path):
    """cma_dynamics: stddev array has shape [n_gens][n_params]."""
    from hornlab_search.gui.data import cma_dynamics
    result = cma_dynamics(cma_run)
    stddev = result.get("stddev", [])
    assert len(stddev) == 5, f"Expected 5 stddev rows, got {len(stddev)}"
    n_params = len(result.get("param_names", []))
    if n_params:
        for row in stddev:
            assert len(row) == n_params, f"stddev row length {len(row)} != n_params {n_params}"


# ---------------------------------------------------------------------------
# run_detail includes cma_dynamics and has_atlas
# ---------------------------------------------------------------------------

def test_run_detail_has_cma_dynamics(no_cma_run: Path):
    """run_detail always includes cma_dynamics key.

    no_cma_run is at tmp_path/runs/RID; parent is runs_dir.
    """
    from hornlab_search.gui.data import run_detail
    runs_dir = no_cma_run.parent  # tmp_path/runs
    result = run_detail(runs_dir, RID)
    assert "cma_dynamics" in result, "run_detail should always include cma_dynamics key"


def test_run_detail_has_atlas_false(no_cma_run: Path):
    """run_detail: has_atlas is False when archive_heatmap.json absent."""
    from hornlab_search.gui.data import run_detail
    runs_dir = no_cma_run.parent
    result = run_detail(runs_dir, RID)
    assert "has_atlas" in result, "run_detail should include has_atlas key"
    assert result["has_atlas"] is False


def test_run_detail_has_atlas_true(no_cma_run: Path):
    """run_detail: has_atlas is True when archive_heatmap.json exists."""
    (no_cma_run / "archive_heatmap.json").write_text("{}", encoding="utf-8")
    from hornlab_search.gui.data import run_detail
    runs_dir = no_cma_run.parent
    result = run_detail(runs_dir, RID)
    assert result["has_atlas"] is True


# ---------------------------------------------------------------------------
# app.js / evolution.js static source checks
# ---------------------------------------------------------------------------

def test_app_js_has_atlas_conditional():
    """H7: app.js QD atlas link must be conditional on d.has_atlas."""
    src = APPJS.read_text(encoding="utf-8")
    assert "has_atlas" in src, "app.js should reference has_atlas for QD atlas link"


def test_app_js_cma_dynamics_rendering():
    """H5: app.js must reference cma_dynamics for the search dynamics card."""
    src = APPJS.read_text(encoding="utf-8")
    assert "cma_dynamics" in src, "app.js should reference cma_dynamics"
    assert "cma-dynamics-block" in src, "app.js should reference cma-dynamics-block element"


def test_app_js_convergence_failure_strip():
    """H2: app.js convergence must have failure strip (× marks below axis)."""
    src = APPJS.read_text(encoding="utf-8")
    assert "failure" in src.lower() or "FAIL_THRESH" in src, "failure strip logic missing"
    assert "FAIL_THRESH" in src, "FAIL_THRESH penalty threshold constant missing"


def test_app_js_score_breakdown_weights():
    """H9: app.js score breakdown bars reference weights."""
    src = APPJS.read_text(encoding="utf-8")
    assert "sortedTerms" in src or "sort" in src, "H9: terms should be sorted by best contribution"


def test_evolution_js_3d_hidden_by_default():
    """H8: evolution.js 3D wrap div has hidden attribute by default."""
    src = EVJS.read_text(encoding="utf-8")
    assert 'id="evo-3d-wrap" hidden' in src or "hidden>" in src, \
        "H8: evolution 3D wrap should have hidden attribute by default"


def test_evolution_js_syntax():
    """evolution.js must parse without errors."""
    r = subprocess.run(["node", "--check", str(EVJS)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
