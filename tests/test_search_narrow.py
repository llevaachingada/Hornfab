"""B.3 (day 2026-11-12): ``hornlab-search narrow --run <dir> [--widen]`` — writes a copy of the
run's config.yaml where ONLY the bounds (from the run's own wall analysis), search.seed (+1)
and name change, with a header comment listing every change and why. Walled sides are never
narrowed; --widen extends them; knobs walled in >50% of all valid rows are flagged for pinning.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.cli import main
from hornlab_search.search import pin_from_cma
from hornlab_search.search.evaluate import append_ndjson
from hornlab_search.search.rundir import write_json_atomic

BOUNDS = {
    "walled_hi": {"lo": 0.0, "hi": 10.0},       # top decile hugging hi: not narrowed; widen +
    "free_mid": {"lo": 0.0, "hi": 10.0},        # top decile mid-box: narrowed to [span + pad]
    "lo_hugging": {"lo": 0.0, "hi": 10.0},      # >50% of ALL rows at lo -> pin candidate
}
ROWS = ([{"n": i, "ok": True, "kind": "", "objective": 1.0 + i, "cached": False,
          "design_hash": f"a{i}", "params": {"walled_hi": 9.99, "free_mid": 5.0,
                                             "lo_hugging": 0.001}}
         for i in range(10)]
        + [{"n": 100 + i, "ok": True, "kind": "", "objective": 9.0 - 0.1 * i, "cached": False,
            "design_hash": f"b{i}", "params": {"walled_hi": 9.98 + 0.001 * i, "free_mid": 5.2,
                                               "lo_hugging": 0.000}}
           for i in range(10)])


def _fake_run(tmp_path, name="r0"):
    rd = tmp_path / name
    rd.mkdir(parents=True, exist_ok=True)
    doc = {"name": "testcase", "family": "OSSE",
           "seed_params": {"walled_hi": 5.0, "free_mid": 5.0, "lo_hugging": 5.0},
           "bounds": json.loads(json.dumps(BOUNDS)),
           "mesh": {"epw": 6.0}, "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234,
                                            "budget": 60, "tolfun": 1e-3}}
    (rd / "config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    for r in ROWS:
        append_ndjson(rd / "search.ndjson", r)
    write_json_atomic(rd / "run.json", {"family": "OSSE", "config_name": "testcase",
                                        "config_sha": "deadbeef"})
    return rd


def _parse(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_wall_analysis_counts_the_walls(tmp_path):
    rd = _fake_run(tmp_path)
    analysis = pin_from_cma.wall_analysis(ROWS, BOUNDS, family="OSSE")
    k = analysis["knobs"]
    assert analysis["top_decile_n"] == 2              # 20 valid rows -> ceil(0.2)
    assert k["walled_hi"]["wall_hi_frac_top"] == 1.0
    assert k["free_mid"]["wall_hi_frac_top"] == 0.0
    assert k["lo_hugging"]["wall_lo_frac_all"] == 1.0


def test_narrow_changes_only_walled_mid_and_flags_pin_candidates(tmp_path):
    rd = _fake_run(tmp_path)
    analysis = pin_from_cma.wall_analysis(ROWS, BOUNDS, family="OSSE")
    nb, changes, pins = pin_from_cma.narrow_bounds(analysis, BOUNDS)
    # walled at hi (1.0 >= 0.5): walled_hi must NOT be narrowed at the HI side;
    # its unused low part still narrows to the top-decile span minus the pad.
    assert nb["walled_hi"]["hi"] == BOUNDS["walled_hi"]["hi"]
    assert nb["walled_hi"]["lo"] == pytest.approx(9.99 - 0.1 * 10.0)   # 8.99 (top decile = the two best rows, both 9.99)
    # The top decile = the two best rows (both from the first group): free_mid sits at 5.0
    # -> narrowed to [4.0, 6.0] with the 1.0-span pad.
    assert nb["free_mid"]["lo"] == pytest.approx(4.0)
    assert nb["free_mid"]["hi"] == pytest.approx(6.0)
    # lo_hugging: >50% of all rows at lo -> pin candidate, and its lo is NOT narrowed
    # (the wall side stays put); its unused high part does narrow.
    assert "lo_hugging" in pins
    assert nb["lo_hugging"]["lo"] == 0.0
    assert nb["lo_hugging"]["hi"] == pytest.approx(1.001)
    keys = {c["key"] for c in changes}
    assert keys == {"free_mid", "walled_hi", "lo_hugging"}


def test_widen_extends_the_walled_side_beyond_the_border(tmp_path):
    rd = _fake_run(tmp_path)
    analysis = pin_from_cma.wall_analysis(ROWS, BOUNDS, family="OSSE")
    nb, changes, _ = pin_from_cma.narrow_bounds(analysis, BOUNDS, widen=True)
    assert nb["walled_hi"]["hi"] == pytest.approx(10.0 + 0.1 * 10.0)
    assert nb["walled_hi"]["lo"] == pytest.approx(9.99 - 0.1 * 10.0)   # narrowed low side stays


def test_cli_narrow_writes_a_config_that_differs_in_exactly_the_allowed_keys(tmp_path, capsys):
    rd = _fake_run(tmp_path)
    out = tmp_path / "sub" / "testcase_narrow.yaml"
    rc = main(["narrow", "--run", str(rd), "--out", str(out)])
    assert rc == 0
    doc = _parse(out)
    orig = _parse(rd / "config.yaml")
    # ONLY bounds / search.seed / name (and the file header) may change
    allowed = {"bounds", "search", "name"}
    rest_orig = {k: v for k, v in orig.items() if k not in allowed}
    rest_new = {k: v for k, v in doc.items() if k not in allowed}
    assert rest_new == rest_orig
    assert doc["search"]["seed"] == orig["search"]["seed"] + 1
    assert doc["name"] == orig["name"] + "_narrow"
    assert doc["bounds"] != orig["bounds"]
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("# NARROW-BOUNDS FOLLOW-UP")
    text = out.read_text(encoding="utf-8")
    assert "free_mid" in text and "Everything else identical" in text
    assert "seed 1234->1235" in text
    assert "PIN CANDIDATE lo_hugging" in text
    # the run dir itself is untouched
    assert _parse(rd / "config.yaml") == orig


def test_cli_narrow_widen_runs_and_reports(tmp_path, capsys):
    rd = _fake_run(tmp_path)
    out = tmp_path / "testcase_widen.yaml"
    rc = main(["narrow", "--run", str(rd), "--widen", "--out", str(out)])
    assert rc == 0
    doc = _parse(out)
    assert doc["name"].endswith("_widen")
    assert doc["bounds"]["walled_hi"]["hi"] == pytest.approx(11.0)
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("# WIDENED-BOUNDS FOLLOW-UP")


def test_narrow_refuses_a_run_without_config_or_rows(tmp_path, capsys):
    rd = _fake_run(tmp_path)
    orphan = tmp_path / "orphan"
    orphan.mkdir()
    rc = main(["narrow", "--run", str(orphan), "--out", str(tmp_path / "x.yaml")])
    assert rc == 1
    assert "narrow FAILED" in capsys.readouterr().out
    rd2 = _fake_run(tmp_path, name="r2")
    (rd2 / "search.ndjson").unlink()
    rc = main(["narrow", "--run", str(rd2), "--out", str(tmp_path / "y.yaml")])
    assert rc == 1
