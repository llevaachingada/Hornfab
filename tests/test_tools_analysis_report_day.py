"""A.8 report_day.py — one YAML spec -> one REPORT.md with every section's outputs.

The spec exercises every tool lane with SYNTHETIC tmp_path run dirs (no real data):
convergence, seed_groups (same brief/family, different cma_seed), sensitivity, links,
walls, ab_compare, term_balance and fidelity; plus one deliberately broken run dir that
must become a recorded `error` section WITHOUT aborting the rest (exit code 0).
"""
from __future__ import annotations

import json

import yaml

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, v4_terms, write_run)

rd = load_tool("report_day")

W = BASE_CONFIG["weights"]
TOL = BASE_CONFIG["objective"]["tolerances"]

N_ROWS = 30
N_VERIFY = 5            # the 5 best screen designs (i = 25..29) get a verify solve


def _raw(i: int) -> dict:
    return {"cov": 0.02 + 0.01 * (i % 8), "rip": 1.0, "di": 1.0, "dislope": 0.5,
            "flat": 1.0, "load": 0.5, "distd": 2.0, "diag": 1.0}


def _terms_run(tmp_path, name, seed, verify_pairs=0):
    """A v4 run with per-row terms; its `verify_pairs` best screen designs are
    re-solved as verify rows (J_verify = 1.3 * J_screen)."""
    rows = [make_row(i, 100.0 - i, terms=v4_terms(_raw(i), W, TOL)) for i in range(N_ROWS)]
    for k in range(verify_pairs):
        i = N_ROWS - 1 - k
        rows.append(make_row(N_ROWS + k, 1.3 * (100.0 - i),
                             design_hash=f"dh{i:04d}", mode="verify",
                             n=N_ROWS + 10 + k, params={"a_deg": 10.0 + k}))
    return write_run(rows, tmp_path, name, seed=seed)


def _verify_subdir(run, k_max):
    """Some of the same designs re-verified in a real verify/ sub-run (union = 5 pairs)."""
    vdir = run / "verify"
    vdir.mkdir(exist_ok=True)
    rows = []
    for k in range(k_max):
        i = N_ROWS - 1 - k
        rows.append(make_row(100 + k, 1.3 * (100.0 - i), design_hash=f"dh{i:04d}",
                             mode="verify", n=100 + k, params={"a_deg": 10.0 + k}))
    (vdir / "search.ndjson").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8")


def _spec(tmp_path) -> dict:
    return {
        "runs_root": str(tmp_path),
        "convergence": [{"id": "g1", "run": "runA"},
                        {"id": "boom", "run": "DOES_NOT_EXIST"}],
        "seed_groups": [{"id": "gseeds", "seeds": ["runA", "runB"]}],
        "sensitivity": [{"id": "g1", "run": "runA"}],
        "links": [{"id": "g1", "run": "runA"}],
        "walls": [{"id": "g1", "run": "runA"}],
        "ab_compare": [{"id": "g3-g4", "a": ["runA"], "b": ["runB"],
                        "label_a": "narrow", "label_b": "control"}],
        "term_balance": [{"id": "tb1", "run": "runA"}],
        "fidelity": [{"id": "fid1", "run": "runA"}],
    }


def _build_runs(tmp_path):
    run_a = _terms_run(tmp_path, "runA", seed=1030, verify_pairs=5)
    _verify_subdir(run_a, 3)                          # union with embedded = 5 verifications
    run_b = _terms_run(tmp_path, "runB", seed=1031)   # same provenance, other seed
    return run_a, run_b


EXPECTED_IDS = ["g1", "boom", "gseeds", "g1", "g1", "g1", "g3-g4", "tb1", "fid1"]
OUT_SUBS = ["convergence_g1", "seed_variance_gseeds",
            "sensitivity_g1", "links_g1", "walls_g1", "ab_compare_g3-g4",
            "term_balance_tb1", "fidelity_fid1"]


# ------------------------------------------------------------------ in-process

def test_run_sections_statuses_and_outputs(tmp_path):
    _build_runs(tmp_path)
    out = tmp_path / "out"
    sections = rd.run_sections(_spec(tmp_path), out)
    assert [s["id"] for s in sections] == EXPECTED_IDS
    boom = next(s for s in sections if s["id"] == "boom")
    assert boom["status"] == "error" and "FileNotFoundError" in (boom["error"] or "")
    ok = [s for s in sections if s["status"] == "ok"]
    assert len(ok) == 8 and len(sections) == 9
    for sub in OUT_SUBS:
        assert (out / sub).is_dir(), sub
    # the chart passthrough really landed (schema: REPORT links each section's PNGs too)
    assert (out / "convergence_g1" / "convergence_1.png").exists()
    assert (out / "term_balance_tb1" / "term_balance.png").exists()
    assert (out / "fidelity_fid1" / "fidelity.png").exists()
    # seed group = same brief/family, seeds 1030/1031 -> one group, no verdict (< 5)
    sv = json.loads((out / "seed_variance_gseeds" / "seed_variance.json").read_text("utf-8"))
    assert sv["groups"]["gseeds"]["n_seeds"] == 2 and sv["verdicts"] == []
    # fidelity pairs 5 designs appearing on both sides
    fid = json.loads((out / "fidelity_fid1" / "fidelity.json").read_text("utf-8"))
    assert fid["n_pairs"] == 5 and fid["bias_median_pct"] >= 30.0   # 1.3x verified


def test_make_report_md_links_sections_and_embeds_md(tmp_path):
    _build_runs(tmp_path)
    out = tmp_path / "out"
    sections = rd.run_sections(_spec(tmp_path), out)
    md = rd.make_report_md(sections, "spec.yaml")
    assert "# Day analysis report" in md
    for sid in ["**g1**", "**boom**", "**gseeds**", "**g3-g4**", "**tb1**", "**fid1**"]:
        assert sid in md
    assert "`FileNotFoundError" in md
    # each healthy section's JSON path line plus its embedded md body
    assert "term_balance_tb1" in md and "Share of J per term" in md


# ------------------------------------------------------------------------ CLI

def test_cli_spec_to_report(tmp_path):
    _build_runs(tmp_path)
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(_spec(tmp_path)), encoding="utf-8")
    out = tmp_path / "report"
    proc = run_cli("report_day", ["--spec", str(spec_path)], tmp_path, out="report")
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "report_day")
    assert doc["tool"] == "report_day" and doc["spec"].endswith("spec.yaml")
    assert doc["n_sections"] == 9 and doc["n_ok"] == 8 and doc["n_error"] == 1
    report = (out / "REPORT.md").read_text(encoding="utf-8")   # schema names REPORT.md
    assert "**boom**" in report and "Status: **error**" in report
    assert (out / "convergence_g1" / "convergence.json").exists()


def test_cli_bad_spec_is_exit_2(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string\n", encoding="utf-8")
    proc = run_cli("report_day", ["--spec", str(bad)], tmp_path)
    assert proc.returncode == 2 and "not a YAML mapping" in proc.stderr
