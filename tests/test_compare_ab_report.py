"""A/B check: report generation (self-contained HTML, summary.json, verdict.txt) with both chart backends."""
import json
import re

import pytest

from hornlab_search.compare import analysis as an, bl_import as bi, charts, fake, hornfab_side as hs
from hornlab_search.compare.report import build_report, verdict_text


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    d = tmp_path_factory.mktemp("pair")
    fake.write_hornfab_side(d / "a", fake.FAKE_FREQS[::2])
    fake.write_bl_gui_side(d / "b", fake.FAKE_FREQS[::2], inject="offset6")
    return hs.load_hornfab(d / "a"), bi.import_bl(d / "b")


def test_report_files_summary_and_verdict(pair, tmp_path):
    cmp = an.compare(*pair)
    res = build_report(cmp, tmp_path, backend="builtin", provenance={"x": 1})
    for name in ("report.html", "summary.json", "verdict.txt", "comparison_arrays.npz"):
        assert (tmp_path / name).exists()
    s = json.loads((tmp_path / "summary.json").read_text())
    assert s["overall"] == "fail" == res["overall"]
    assert s["metrics"]["on_axis_abs"]["bands"]["1-5k"]["median"] == pytest.approx(-6.02, abs=0.01)
    assert "starting points" in s["tolerance_note"] and s["chart_backend"] == "builtin"
    assert any(f["code"] == "constant_offset" for f in s["convention_findings"])
    txt = (tmp_path / "verdict.txt").read_text()
    assert txt.startswith("A/B VERDICT: FAIL") and "half-space" in txt and "LIKELY CAUSES" in txt


def test_html_is_self_contained_and_has_all_sections(pair, tmp_path):
    build_report(an.compare(*pair), tmp_path, backend="builtin")
    h = (tmp_path / "report.html").read_text()
    assert not re.search(r'(src|href)="https?://', h) and "<script" not in h          # nothing fetched, nothing executed
    assert h.count("<svg") >= 8 and h.count("data:image/png;base64,") >= 6
    for title in ("On-axis frequency response", "Off-axis, H plane", "H polar map", "V polar map", "-6 dB beamwidth",
                  "Directivity index", "Balloon", "On-axis phase", "Throat impedance", "Verdict table", "Provenance"):
        assert title in h
    assert "prefers-color-scheme" in h and "viewport" in h


def test_verdict_text_lists_every_metric_and_band(pair):
    cmp = an.compare(*pair)
    t = verdict_text(cmp, [])
    for _, m in cmp.metrics.items():
        assert m.title[:40] in t
    for b in ("<1k", "1-5k", "5-10k", ">10k"):
        assert b in t


def test_missing_data_sections_are_omitted_not_faked(tmp_path):
    a = fake.fake_response(fake.FAKE_FREQS[:12], balloon_points=100)
    a.p_h = a.p_v = a.p_balloon = a.z_throat = None
    A = hs.from_response(a)
    fake.write_bl_gui_side(tmp_path / "b", fake.FAKE_FREQS[:12], with_impedance=False)
    cmp = an.compare(A, bi.import_bl(tmp_path / "b"))
    build_report(cmp, tmp_path / "r", backend="builtin")
    h = (tmp_path / "r" / "report.html").read_text()
    assert "Throat impedance" not in h and "On-axis phase" not in h
    assert any("impedance skipped" in n for n in cmp.notes) and any("phase skipped" in n for n in cmp.notes)


def test_matplotlib_backend_when_installed(pair, tmp_path):
    pytest.importorskip("matplotlib")
    build_report(an.compare(*pair), tmp_path, backend="matplotlib")
    h = (tmp_path / "report.html").read_text()
    assert h.count("data:image/png;base64,") >= 15 and "<svg" not in h.split("<h2>Provenance")[0]


def test_charts_fall_back_without_matplotlib_and_handle_empty_input():
    assert "<svg" in charts.line_chart("t", "x", "y", [{"label": "a", "x": [1, 10, 100], "y": [0, 1, 0.5]}], backend="builtin")
    assert "no data" in charts.line_chart("t", "x", "y", [], backend="builtin")
    assert "no data" in charts.heat_chart("t", [1, 2], [0, 1], None, vmin=0, vmax=1, backend="builtin")
