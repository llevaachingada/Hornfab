"""Group E.1 analysis-page tests: read-only rendering of the Group A tool outputs.

The fixtures write the exact JSON files `tools/analysis/*` produce (schema revision
2026-11-12, per `git show day/A-analysis:tools/analysis/schema.md`) under a synthetic
``runs/analysis/``, plus unknown-tool and malformed extras to prove defensive reading. No
analysis is ever executed and no solve runs.
"""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App, make_handler

GEN = "2026-11-12T18:00:00Z"

CONVERGENCE = {
    "tool": "convergence", "generated_utc": GEN,
    "runs": [
        {"run_dir": "runs/20261111T000000Z-screen-aaaaaa", "brief": "seed1030", "family": "OSSE",
         "objective_version": 4, "n_new_valid": 3, "final_best": 12.34,
         "curve": [{"n": 1, "best": 22.5, "wall_s": 19.0},
                   {"n": 2, "best": 15.0, "wall_s": 38.0},
                   {"n": 3, "best": 12.34, "wall_s": 60.0}],
         "evals_to_5pct": 2, "evals_to_1pct": None, "last20_improvement": False,
         "brand_new_field_day_a_may_add": {"x": 1}},
        {"run_dir": "runs/20261111T000001Z-screen-bbbbbb", "brief": "seed1031", "family": "OSSE",
         "objective_version": 4, "n_new_valid": 2, "final_best": 18.0,
         "curve": [{"n": 1, "best": 30.0}, {"n": 2, "best": 18.0}],
         "evals_to_5pct": None, "last20_improvement": True},
    ],
}
SEED_VARIANCE = {
    "tool": "seed_variance", "generated_utc": GEN,
    "seed_rule": "A beats B only when medians differ by more than both spreads",
    "groups": {"g1": {"n_seeds": 2,
                      "seeds": [{"run_dir": "r1", "cma_seed": 1030, "best_j": 12.3},
                                {"run_dir": "r2", "cma_seed": 1031, "best_j": 14.5}],
                      "median_best": 13.4, "spread_best": 2.2, "ci95_median_best": [11.0, 15.9]},
               "g2": {"n_seeds": 1, "seeds": [{"run_dir": "r3", "best_j": 40.0}],
                      "median_best": 40.0, "spread_best": 0.0, "ci95_median_best": None}},
    "verdicts": [
        {"a": "g1", "b": "g2", "median_a": 13.4, "median_b": 40.0, "spread_a": 2.2,
         "spread_b": 0.5, "n_seeds": 2, "verdict": "indicative", "rule_holds": True},
    ],
}
SENSITIVITY = {
    "tool": "sensitivity", "generated_utc": GEN, "run_dir": "r1", "n_valid": 110,
    "spearman": [{"key": "a_deg", "rho": -0.41, "rho_abs": 0.41, "n": 110},
                 {"key": "L_mm", "rho": 0.2, "rho_abs": 0.2, "n": 110}],
    "top_decile_shift": [{"key": "a_deg", "mean_all": 41.2, "mean_top": 38.7,
                          "shift_norm": -0.03}],
    "surrogate": None,
}
LINKS = {
    "tool": "links", "generated_utc": GEN, "run_dir": "r1",
    "pairs": [{"a": "a_deg", "b": "n", "rho": -0.72,
               "fit": {"scale": 0.104, "offset": 1.88, "r2": 0.55}}],
    "cma_directions": [{"rank": 1, "eigenvalue": 0.42, "fraction": 0.61,
                        "keys": ["a_deg", "n"]}],
    "proposed_links": [{"knob_b": "n", "knob_a": "a_deg", "scale": 0.104, "offset": 1.88,
                        "r2": 0.55, "source": "rho_top_decile"}],
}
WALLS = {
    "tool": "walls", "generated_utc": GEN, "run_dir": "r1",
    "walls": [{"key": "L_mm", "lo": 140.0, "hi": 420.0, "frac_lo": 0.18, "frac_hi": 0.55,
               "wall_hi": True, "wall_lo": False}],
    "proposal": [{"key": "L_mm", "action": "widen_hi", "new_lo": 156.0, "new_hi": 462.0,
                  "reason": "55% of top-decile within 3% of hi; top-decile range padded 5%"}],
}
REPORT_MD = "# Day report\n\nSeed group g1: see tables.\n"


def _write(base: Path, name: str, payload) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / name).write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def analysis(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    adir = root / "runs" / "analysis"
    day1 = adir / "day_2026-11-12"
    for name, payload in (("convergence.json", CONVERGENCE), ("seed_variance.json", SEED_VARIANCE),
                          ("sensitivity.json", SENSITIVITY), ("links.json", LINKS),
                          ("walls.json", WALLS)):
        _write(day1, name, payload)
    (day1 / "REPORT.md").write_text(REPORT_MD, encoding="utf-8")
    # a second set: one valid header-less tool + one malformed JSON + one unknown tool
    day2 = adir / "other_day"
    day2.mkdir(parents=True)
    (day2 / "convergence.json").write_text("{not json", encoding="utf-8")
    _write(day2, "custom_extra.json", {"anything": True})
    # top-level files belong to the "." set
    _write(adir, "convergence.json", {"tool": "convergence", "generated_utc": GEN, "runs": []})
    return root, root / "runs", adir


def test_analysis_sets_listing(analysis):
    root, _, adir = analysis
    sets = {s["id"]: s for s in D.analysis_sets(adir)}
    assert set(sets) == {".", "day_2026-11-12", "other_day"}
    assert sets["day_2026-11-12"]["tools"] == [
        "convergence", "seed_variance", "sensitivity", "links", "walls"]
    assert sets["day_2026-11-12"]["has_report_md"] is True
    assert sets["day_2026-11-12"]["generated_utc"] == GEN
    assert sets["other_day"]["tools"] == []            # malformed convergence: skipped, not crashed
    assert sets["."]["tools"] == ["convergence"]
    assert D.analysis_sets(root / "nowhere") == []


def test_analysis_report_passes_payloads_through(analysis):
    _, runs, adir = analysis
    d = D.analysis_report(adir, "day_2026-11-12")
    assert d["id"] == "day_2026-11-12" and d["generated_utc"] == GEN
    conv = d["convergence"]
    assert len(conv["runs"]) == 2
    assert [p["best"] for p in conv["runs"][0]["curve"]] == [22.5, 15.0, 12.34]
    assert conv["runs"][0]["brand_new_field_day_a_may_add"] == {"x": 1}   # unknown fields ride along
    assert d["seed_variance"]["verdicts"][0]["verdict"] == "indicative"
    assert d["links"]["proposed_links"][0]["r2"] == 0.55
    assert d["walls"]["walls"][0]["wall_hi"] is True
    assert d["report_md"] == REPORT_MD and d["report_md_truncated"] is False


def test_analysis_report_defensive_cases(analysis):
    _, runs, adir = analysis
    d = D.analysis_report(adir, "other_day")
    assert d["tools"] == [] and d["extra_tools"] == ["custom_extra"]
    assert "report_md" not in d and "convergence" not in d
    with pytest.raises(ValueError):
        D.analysis_report(adir, "../..")
    with pytest.raises(FileNotFoundError):
        D.analysis_report(adir, "no_such_set")
    with pytest.raises(ValueError):
        D.analysis_report(adir, "bad name")


def test_analysis_api_routes(analysis):
    root, runs, adir = analysis
    app = App(root, runs)
    idx = app.get("/api/analysis", {})
    assert {s["id"] for s in idx} == {".", "day_2026-11-12", "other_day"}
    det = app.get("/api/analysis/day_2026-11-12", {})
    assert det["seed_variance"]["groups"]["g1"]["n_seeds"] == 2
    # the analysis folder is configurable through the App constructor
    other = App(root, runs, analysis_dir=adir / "day_2026-11-12").get("/api/analysis", {})
    assert [(s["id"], s["tools"]) for s in other] == [
        (".", ["convergence", "seed_variance", "sensitivity", "links", "walls"])]


# ------------------------------------------------------------------ nested report_day sets
#
# `report_day.py` writes one subdirectory per section (convergence_g1/, walls_g6/, …), not the
# flat `<tool>.json` layout above. These payloads mirror the real evidence fixture's shape:
# seven tools reach the set (six section tools + root report_day.json), twelve section dirs,
# and one honest refusal (`v6_seeds`) that has no output directory.

NESTED_GEN = "2026-11-12T23:30:10Z"

NESTED_CONV_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa", "brief": "atlas__core_law",
    "family": "OSSE", "objective_version": 4,
    "curve": [{"n": 1, "best": 22.5}, {"n": 2, "best": 12.34}],
    "last20_improvement": False,
}
NESTED_SENS_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa", "n_valid": 110,
    "spearman": [{"key": "a_deg", "rho": -0.41, "rho_abs": 0.41, "n": 110}],
}
NESTED_LINKS_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa",
    "proposed_links": [{"knob_b": "n", "knob_a": "a_deg", "scale": 0.104, "offset": 1.88,
                        "r2": 0.55}],
}
NESTED_WALLS_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa",
    "walls": [{"key": "L_mm", "lo": 140.0, "hi": 420.0, "frac_lo": 0.18, "frac_hi": 0.55,
               "wall_hi": True, "wall_lo": False}],
}
NESTED_TERM_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa",
    "shares": {"median": {"a_deg": 0.5, "L_mm": 0.5}},
}
NESTED_FIDELITY_G1 = {
    "run_dir": "runs/20261111T000000Z-screen-aaaaaa",
    "bias_median_pct": 3.2, "spearman_all": 0.7, "n_pairs": 8,
}

#: section directory -> (tool, payload). Twelve physical sections, six tools.
NESTED_SECTIONS = {
    "convergence_c2": ("convergence", {"brief": "c2", "family": "OSSE",
                                       "objective_version": 4, "curve": [{"n": 1, "best": 9.0}]}),
    "convergence_g1": ("convergence", NESTED_CONV_G1),
    "convergence_g8": ("convergence", {"brief": "g8", "family": "OSSE",
                                       "objective_version": 4, "curve": [{"n": 1, "best": 8.0}]}),
    "convergence_g9": ("convergence", {"brief": "g9", "family": "OSSE",
                                       "objective_version": 4, "curve": [{"n": 1, "best": 7.0}]}),
    "sensitivity_g1": ("sensitivity", NESTED_SENS_G1),
    "sensitivity_g6": ("sensitivity", {"run_dir": "runs/x", "n_valid": 20, "spearman": []}),
    "links_g1": ("links", NESTED_LINKS_G1),
    "walls_g1": ("walls", NESTED_WALLS_G1),
    "walls_g6": ("walls", {"run_dir": "runs/x", "walls": []}),
    "term_balance_g1": ("term_balance", NESTED_TERM_G1),
    "term_balance_g6": ("term_balance", {"run_dir": "runs/x",
                                         "shares": {"median": {"a_deg": 1.0}}}),
    "fidelity_g1": ("fidelity", NESTED_FIDELITY_G1),
}

NESTED_ERROR = ("ValueError: group 'v6_seeds' is not one task/scoring identity: "
                "['task_config_hash_mismatch']")
NESTED_REPORT_DAY = {
    "tool": "report_day", "generated_utc": NESTED_GEN,
    "n_sections": 13, "n_ok": 12, "n_error": 1,
    "sections": [
        {"id": "g1", "tool": "convergence", "status": "ok"},
        {"id": "c2", "tool": "convergence", "status": "ok"},
        {"id": "g8", "tool": "convergence", "status": "ok"},
        {"id": "g9", "tool": "convergence", "status": "ok"},
        {"id": "v6_seeds", "tool": "seed_variance", "status": "error", "error": NESTED_ERROR},
        {"id": "g1", "tool": "sensitivity", "status": "ok"},
        {"id": "g6", "tool": "sensitivity", "status": "ok"},
        {"id": "g1", "tool": "links", "status": "ok"},
        {"id": "g1", "tool": "walls", "status": "ok"},
        {"id": "g6", "tool": "walls", "status": "ok"},
        {"id": "g1", "tool": "term_balance", "status": "ok"},
        {"id": "g6", "tool": "term_balance", "status": "ok"},
        {"id": "g1", "tool": "fidelity", "status": "ok"},
    ],
}

#: expected sections order: (tool order per ANALYSIS_TOOL_JSONS, section id)
NESTED_EXPECTED_SECTIONS = [
    ("convergence_c2", "convergence"),
    ("convergence_g1", "convergence"),
    ("convergence_g8", "convergence"),
    ("convergence_g9", "convergence"),
    ("sensitivity_g1", "sensitivity"),
    ("sensitivity_g6", "sensitivity"),
    ("links_g1", "links"),
    ("walls_g1", "walls"),
    ("walls_g6", "walls"),
    ("term_balance_g1", "term_balance"),
    ("term_balance_g6", "term_balance"),
    ("fidelity_g1", "fidelity"),
]


@pytest.fixture()
def nested(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "nested_repo"
    adir = root / "runs" / "analysis"
    day = adir / "day_2026-11-12"
    for sid, (tool, payload) in NESTED_SECTIONS.items():
        sub = day / sid
        _write(sub, f"{tool}.json", payload)
        (sub / f"{tool}.md").write_text(f"# {sid}\n", encoding="utf-8")
        if sid == "convergence_g1":
            (sub / "convergence_1.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        elif sid in ("links_g1", "walls_g1", "term_balance_g1", "fidelity_g1"):
            (sub / f"{tool}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    _write(day, "report_day.json", NESTED_REPORT_DAY)
    (day / "REPORT.md").write_text("# Day report\n", encoding="utf-8")
    (day / "report_day.md").write_text("# day\n", encoding="utf-8")
    # a second set whose report_day.json is genuinely malformed (not merely wrong-shaped)
    bad = adir / "bad_day"
    (bad / "fidelity_g1").mkdir(parents=True)
    _write(bad / "fidelity_g1", "fidelity.json", {"run_dir": "runs/y"})
    (bad / "report_day.json").write_text("{not json", encoding="utf-8")
    return root, root / "runs", adir


@pytest.fixture()
def nested_server(nested):
    root, runs, adir = nested
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port),
                                make_handler(App(root, runs, analysis_dir=adir), port))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_nested_set_lists_tools_sections_and_errors(nested):
    _, _, adir = nested
    sets = {s["id"]: s for s in D.analysis_sets(adir)}
    day = sets["day_2026-11-12"]
    assert day["tools"] == ["convergence", "sensitivity", "links", "walls",
                            "term_balance", "fidelity", "report_day"]
    assert day["n_sections"] == 12
    assert day["n_errors"] == 1
    assert day["has_report_md"] is True
    assert day["generated_utc"] == NESTED_GEN
    assert sets["bad_day"]["n_sections"] == 1 and sets["bad_day"]["n_errors"] == 0


def test_nested_report_sections_payloads(nested):
    _, _, adir = nested
    d = D.analysis_report(adir, "day_2026-11-12")
    assert d["n_sections"] == 12 and len(d["sections"]) == 12
    assert [(s["id"], s["tool"]) for s in d["sections"]] == NESTED_EXPECTED_SECTIONS
    by_id = {s["id"]: s for s in d["sections"]}
    for sid, (_tool, payload) in NESTED_SECTIONS.items():
        assert by_id[sid]["data"] == payload
    g1 = by_id["convergence_g1"]
    assert g1["files"] == ["convergence.json", "convergence.md", "convergence_1.png"]
    assert g1["has_png"] is True and g1["pngs"] == ["convergence_1.png"]
    assert by_id["sensitivity_g1"]["has_png"] is False and by_id["sensitivity_g1"]["pngs"] == []
    assert d["section_index"]["convergence"] == [
        "convergence_c2", "convergence_g1", "convergence_g8", "convergence_g9"]
    assert d["section_index"]["fidelity"] == ["fidelity_g1"]
    assert "seed_variance" not in d["section_index"]     # errored: no output directory


def test_nested_report_errors_are_verbatim(nested):
    _, _, adir = nested
    d = D.analysis_report(adir, "day_2026-11-12")
    assert len(d["errors"]) == 1
    err = d["errors"][0]
    assert err == {"id": "v6_seeds", "tool": "seed_variance", "status": "error",
                   "error": NESTED_ERROR}
    assert "task_config_hash_mismatch" in err["error"]


def test_nested_flat_compatibility_rule(nested):
    _, _, adir = nested
    d = D.analysis_report(adir, "day_2026-11-12")
    # 2+ sections -> no flat key; exactly 1 -> flat key as before; root-only -> flat key
    assert "convergence" not in d
    assert "sensitivity" not in d and "walls" not in d and "term_balance" not in d
    assert d["links"] == NESTED_LINKS_G1
    assert d["fidelity"] == NESTED_FIDELITY_G1
    assert d["report_day"]["tool"] == "report_day"


def test_malformed_report_day_never_raises(nested):
    _, _, adir = nested
    d = D.analysis_report(adir, "bad_day")
    assert d["errors"] == []
    assert d["n_sections"] == 1


def test_analysis_report_refuses_traversal_set_id(nested):
    _, _, adir = nested
    with pytest.raises(ValueError):
        D.analysis_report(adir, "../..")


def _get_raw(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.status, resp.headers.get("Content-Type"), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def test_analysis_file_route_serves_only_contained_known_files(nested_server):
    valid = nested_server + "/analysis/day_2026-11-12/convergence_g1/convergence_1.png"
    code, ctype, body = _get_raw(valid)
    assert code == 200 and ctype == "image/png" and body.startswith(b"\x89PNG")
    code, ctype, _ = _get_raw(nested_server + "/analysis/day_2026-11-12/report_day.json")
    assert code == 200 and ctype == "application/json"
    # traversal set id (encoded separators keep it one path segment)
    assert _get_raw(nested_server + "/analysis/..%2f..%2fetc/day_2026-11-12/convergence_1.png")[0] == 404
    # traversal file name
    assert _get_raw(nested_server + "/analysis/day_2026-11-12/convergence_g1/..%2f..%2f..%2fetc")[0] == 404
    # unknown extension, missing file, and a directory are all refused
    assert _get_raw(nested_server + "/analysis/day_2026-11-12/convergence_g1/convergence.exe")[0] == 404
    assert _get_raw(nested_server + "/analysis/day_2026-11-12/convergence_g1/nope.png")[0] == 404
    assert _get_raw(nested_server + "/analysis/day_2026-11-12/convergence_g1")[0] == 404
