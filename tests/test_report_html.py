"""Tests 19-23 of 08_TASK_PIPELINE: the HTML report, built from synthetic runs."""
from __future__ import annotations

import json
import re

import pytest

from hornlab_search.dataset.store import DatasetStore
from hornlab_search.report.html import build_report
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture
def cfg(smoke_cfg):
    return fast_cfg(smoke_cfg)


def make_run(cfg, tmp_path, monkeypatch, budget=20, backend=None, **fakes):
    be = backend or SyntheticBackend()
    install_fakes(monkeypatch, be, **fakes)
    store = DatasetStore(tmp_path / "ds")
    run_dir = tmp_path / "20261013T000000Z-screen-abc123"
    cma_mod.search(cfg, run_dir, "screen", backend=be, budget=budget, store=store, lib_shas=LIBS,
                   command="hornlab-search search --config examples/search_smoke.yaml --budget 20")
    return run_dir, store


def n_pngs(html):
    return len(re.findall(r"data:image/png;base64,[A-Za-z0-9+/=]{100,}", html))


# 19
def test_report_has_run_id_and_at_least_six_pngs(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch)
    out = build_report(run_dir, tmp_path / "r.html", top_n=2, store=store)
    html = out.read_text(encoding="utf-8")
    assert len(html) > 10_000 and run_dir.name in html
    assert n_pngs(html) >= 6
    assert "hornlab-search search --config" in html          # the reproduction block
    for h in ("Convergence", "Objective term breakdown", "Bounds report", "DI provenance",
              "Dataset", "Reproduction", "Failures", "Feasibility"):
        assert h in html, h
    prov = html.split("<h2>DI provenance</h2>")[1].split("</table>")[0]
    assert "<td>balloon</td>" in prov and "cuts_estimate" not in prov
    assert "f_break" in html and "f11" in html


# 20
def test_report_says_so_when_the_best_is_not_better_than_the_seed(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=12)
    p = run_dir / "search.ndjson"
    rows = read_ndjson(p)
    rows[0]["objective"] = 1e-6                               # make the seed unbeatable
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    html = build_report(run_dir, tmp_path / "r.html", top_n=1, store=store).read_text(encoding="utf-8")
    assert "did NOT improve on the seed" in html
    assert html.index("did NOT improve") < html.index("Run</h2>")      # at the top, before the details


def test_report_states_an_improvement_when_there_is_one(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=30)
    html = build_report(run_dir, tmp_path / "r.html", top_n=1, store=store).read_text(encoding="utf-8")
    assert "% lower" in html and "did NOT improve" not in html


# 21
def test_report_renders_a_run_with_zero_successful_evaluations(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend(fail_on={i: "fail" for i in range(1, 40)})
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=10, backend=be)
    html = build_report(run_dir, tmp_path / "r.html", store=store).read_text(encoding="utf-8")
    assert "No evaluation succeeded" in html and "solve_failed" in html
    assert "noise-floor" in html


def test_report_renders_an_empty_run_directory(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    html = build_report(d, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "No evaluations" in html


# 22
def test_report_under_10_mb_for_200_evaluations(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=200)
    out = build_report(run_dir, tmp_path / "r.html", top_n=5, store=store)
    assert len(read_ndjson(run_dir / "search.ndjson")) == 200
    assert out.stat().st_size < 10 * 1024 * 1024
    assert n_pngs(out.read_text(encoding="utf-8")) >= 6 * 5


# 23
def test_noise_floor_box_and_feasibility_contain_numbers(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=8)
    html = build_report(run_dir, tmp_path / "r.html", top_n=1, store=store, figures=False) \
        .read_text(encoding="utf-8")
    nf = html.split('id="noise-floor"')[1].split("</div>")[0]
    assert "No claimed improvement smaller than this number means anything" in nf
    assert re.search(r"Noise floor: 0\.039 dB \(limited by: two solvers", nf), nf[:200]
    assert "not by mesh refinement" in nf
    assert "above 2.5 kHz" in nf and "<b>not measured</b>" in nf
    assert "NOT YET MEASURED" not in nf and "0.055" not in nf
    assert "tolfun" in nf
    fe = html.split('id="feasibility"')[1].split("</div>")[0]
    assert re.search(r"needs about \d+\.\d+ m of mouth width", fe)
    assert re.search(r"<td>\d+\.\d+</td>", fe)


def test_bounds_report_flags_a_pinned_parameter(cfg, tmp_path, monkeypatch):
    run_dir, store = make_run(cfg, tmp_path, monkeypatch, budget=40)
    html = build_report(run_dir, tmp_path / "r.html", top_n=3, store=store, figures=False) \
        .read_text(encoding="utf-8")
    sec = html.split("Bounds report")[1].split("Failures")[0]
    for k in ("a_deg", "aspect_ratio", "exponent", "L_mm"):
        assert f"<td>{k}</td>" in sec
    assert "r0_mm" not in sec                                 # pinned by the user, not searched
