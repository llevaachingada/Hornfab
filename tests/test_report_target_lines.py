"""Report scoring-truth reference lines (P0, 2026-11-16).

The HTML report must draw the same scored truth the GUI shows: flat H/V targets only over the
scored frequencies (a one-sided lower bound / no guide below onset), the actual 8 kHz floors, and
for DI only the scored level (v2+ Gaussian, never the v1 cuts formula) plus the scored slope
anchored at an explicitly *display-only* intercept. These tests pin the additive ``ref_lines``
primitive and the per-design figures against the same 80x50 / f0=700 / 350-8000 Hz fixture used by
``tests/test_scoring_view.py``.

No scorer is called and no J is recomputed; the report only restates what the scoring view exposes.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from hornlab_search.report.html import PALETTE, _design_figures, _svg_lines
from hornlab_search.targets.spec import Target
from test_scoring_view import (
    BW_H,
    BW_V,
    DI_DB,
    FREQS,
    OBJ_V7,
    TARGET,
    W_V7,
)

DESIGN_HASH = "0123456789ab"
DI_SCALAR_SLOPE = 9.567573280356504      # display-only scalar from the fixture response
DI_GAUSSIAN = 13.079574383820045         # v2+ Gaussian target for 80 x 50
DI_CUTS_WRONG = 10.576418879992264       # the v1 cuts value the old report drew for every version


# --------------------------------------------------------------------------- svg primitive


def _points(svg: str, color: str) -> list[tuple[float, float]]:
    """The 1.2-px reference polyline of ``color`` (measured series are 1.8 px)."""
    m = re.search(r'<polyline[^>]*stroke="' + re.escape(color)
                  + r'" stroke-width="1\.2"[^>]*points="([^"]+)"', svg)
    assert m, f"no reference polyline in {color}"
    return [(float(a), float(b)) for a, b in (pair.split(",") for pair in m.group(1).split())]


def test_ref_line_flat_matches_hline_geometry():
    svg = _svg_lines(
        [{"x": [1.0, 2.0, 3.0, 4.0], "y": [0.0, 1.0, 2.0, 3.0], "label": "m", "color": "#123456"}],
        hlines=[(5.0, "hline", "#000000")],
        ref_lines=[{"pts": [[1.0, 5.0], [4.0, 5.0]], "label": "flat ref", "color": "#111111"}],
        title="refs",
    )
    hl = re.search(r'<line x1="([\d.]+)" x2="([\d.]+)" y1="([\d.]+)" y2="([\d.]+)" '
                   r'stroke="#000000"', svg)
    assert hl, "hline missing"
    hx1, hx2, hy1, hy2 = (float(v) for v in hl.groups())
    assert hy1 == hy2
    pts = _points(svg, "#111111")
    assert [p[0] for p in pts] == [hx1, hx2]
    assert pts[0][1] == pts[1][1] == hy1
    assert "flat ref" in svg
    # Default reference dash is the thin 2 3 pattern.
    assert re.search(r'stroke="#111111" stroke-width="1\.2" stroke-dasharray="2 3"', svg)


def test_ref_line_oblique_draws_and_extends_the_y_range():
    svg = _svg_lines(
        [{"x": [1.0, 2.0, 3.0, 4.0], "y": [0.0, 1.0, 2.0, 3.0], "label": "m", "color": "#123456"}],
        ref_lines=[{"pts": [[1.0, 0.0], [4.0, 9.0]], "label": "oblique target",
                    "color": "#abcdef", "dash": True}],
        title="refs",
    )
    pts = _points(svg, "#abcdef")
    assert pts[0][0] < pts[1][0] and pts[1][1] < pts[0][1]      # rising, y-down SVG
    assert "oblique target" in svg
    assert re.search(r'stroke="#abcdef" stroke-width="1\.2" stroke-dasharray="4 3"', svg)
    ticks = re.findall(r'<text x="47" y="[\d.]+" text-anchor="end" class="tick">([^<]+)</text>', svg)
    assert ticks and max(float(t) for t in ticks) >= 9.0, f"ref y not in the axis range: {ticks}"


# --------------------------------------------------------------------------- design figures


def _write_run(run_dir: Path, metrics: dict) -> dict:
    """Minimal run dir + the ndjson-shaped row ``_designs`` would pass to the figure builder."""
    design_dir = run_dir / "designs" / DESIGN_HASH
    design_dir.mkdir(parents=True)
    (design_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (run_dir / "config.yaml").write_text(
        "# minimal fixture for the report scoring-truth lines (see tests/test_scoring_view.py)\n"
        "name: report-target-lines-fixture\n"
        "family: OSSE\n"
        f"target:\n  coverage_h_deg: {TARGET['coverage_h_deg']}\n"
        f"  coverage_v_deg: {TARGET['coverage_v_deg']}\n"
        f"  band_lo_hz: {TARGET['band_lo_hz']}\n"
        f"  band_hi_hz: {TARGET['band_hi_hz']}\n"
        f"  f0_hz: {TARGET['f0_hz']}\n"
        f"  di_slope_target: {TARGET['di_slope_target']}\n"
        f"objective:\n  version: {OBJ_V7['version']}\n"
        f"  bw8k_floor: {OBJ_V7['bw8k_floor']}\n"
        f"  cov_below_f0: {OBJ_V7['cov_below_f0']}\n"
        "weights:\n" + "".join(f"  {k}: {v}\n" for k, v in W_V7.items()),
        encoding="utf-8",
    )
    return {
        "design_hash": DESIGN_HASH,
        "ok": True,
        "params": {"a_deg": 30.0},
        "metrics": metrics,
    }


def _metrics() -> dict:
    return {
        "freqs_hz": list(FREQS),
        "bw_h_deg": list(BW_H),
        "bw_v_deg": list(BW_V),
        "di_db": list(DI_DB),
        "di_source": "balloon",
        "scalars": {"di_slope_db_per_dec": DI_SCALAR_SLOPE},
    }


def _figures(run_dir: Path, row: dict, weights: dict | None = None) -> dict[str, str]:
    target = Target.from_dict(TARGET)
    inputs = {
        "target_raw": dict(TARGET),
        "objective_raw": dict(OBJ_V7),
        "weights": dict(W_V7 if weights is None else weights),
        "version": int(OBJ_V7["version"]),
    }
    out = _design_figures(run_dir, row, target, "OSSE", {}, scoring_view=inputs)
    return {title: svg for title, svg in out["svgs"]}


def _beamwidth(figures: dict) -> tuple[str, str]:
    return next((t, s) for t, s in figures.items() if t.startswith("Beamwidth"))


def _di(figures: dict) -> tuple[str, str]:
    return next((t, s) for t, s in figures.items() if t.startswith("Directivity index"))


def _px(hz: float) -> float:
    """The chart's log-x pixel for ``hz`` on the 250-8000 Hz fixture (ml=52, pw=556)."""
    return 52.0 + (math.log10(hz) - math.log10(250.0)) / (
        math.log10(8000.0) - math.log10(250.0)) * 556.0


def test_beamwidth_target_starts_at_the_scored_onset_and_shows_8k_floors(tmp_path: Path):
    run_dir = tmp_path / "run"
    row = _write_run(run_dir, _metrics())
    figures = _figures(run_dir, row)
    title, svg = _beamwidth(figures)

    # Scored H/V targets start at 700 Hz (not the 350 Hz band edge).
    h_pts = _points(svg, PALETTE[0])
    v_pts = _points(svg, PALETTE[1])
    assert h_pts[0][0] == pytest.approx(_px(700.0), abs=0.2)
    assert v_pts[0][0] == pytest.approx(_px(700.0), abs=0.2)
    assert h_pts[-1][0] == pytest.approx(_px(8000.0), abs=0.2)
    assert all(p[0] >= _px(700.0) - 0.2 for p in h_pts + v_pts), "target geometry below the onset"
    assert "target H 80°" in svg and "target V 50°" in svg

    # The real 8 kHz one-sided floors are separate constraints, labelled with their values.
    assert "8k floor 60°" in svg and "8k floor 37.5°" in svg

    # mask below f0: no guideline through the unscored region; the title says so.
    assert "below f0: not scored" in title


def test_di_with_di_weight_zero_has_no_level_line_but_the_scored_slope(tmp_path: Path):
    run_dir = tmp_path / "run"
    row = _write_run(run_dir, _metrics())
    from test_scoring_view import W_V7 as w
    figures = _figures(run_dir, row, weights=w)      # di = 0, dislope = 1
    title, svg = _di(figures)

    assert "target DI" not in svg, "an unscored DI level must not be drawn"
    assert "display-only intercept" in svg
    assert "slope target 5 dB/dec" in svg
    assert "scored-band slope 9.568" in title
    assert str(round(DI_CUTS_WRONG, 3)) not in title + svg


def test_di_level_uses_the_v2_gaussian_target_when_the_weight_is_nonzero(tmp_path: Path):
    run_dir = tmp_path / "run"
    row = _write_run(run_dir, _metrics())
    weights = dict(W_V7, di=1.0)
    figures = _figures(run_dir, row, weights=weights)
    title, svg = _di(figures)

    assert f"target DI {DI_GAUSSIAN:.3f}".rstrip("0").rstrip(".") in svg
    assert "target DI 13.08" in svg and "(gaussian)" in svg
    assert str(round(DI_CUTS_WRONG, 3)) not in title + svg, "the v1 cuts formula is not v2+ truth"
    assert "display-only intercept" in svg


def test_di_neither_level_nor_slope_scored_says_so_and_draws_no_target(tmp_path: Path):
    run_dir = tmp_path / "run"
    row = _write_run(run_dir, _metrics())
    figures = _figures(run_dir, row, weights=dict(W_V7, di=0.0, dislope=0.0))
    title, svg = _di(figures)

    assert "target DI" not in svg and "slope target" not in svg
    assert title.endswith(", DI not scored this brief")
