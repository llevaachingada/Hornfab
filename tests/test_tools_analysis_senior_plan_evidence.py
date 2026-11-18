"""Senior-plan evidence driver (2026-11-17): smoke test on a synthetic biradial run."""
import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from tools.analysis import senior_plan_evidence as SPE

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path):
    src = ROOT / "examples" / "typologies" / "home_landscape_2026-11-15" / "hl__biradial_es_style_v7.yaml"
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    if raw.get("brief_file"):
        raw["brief_file"] = str((src.parent / raw["brief_file"]).resolve())
    run = tmp_path / "runs" / "r1"
    (run / "designs" / "h1").mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    seed = DesignSpace.from_config(load_config(run / "config.yaml")).seed
    (run / "designs" / "h1" / "design.json").write_text(json.dumps(
        {"family": seed.family, "params": seed.params, "design_hash": "h1"}, default=float))
    (run / "search.ndjson").write_text(json.dumps(
        {"design_hash": "h1", "ok": True, "kind": "", "objective": 5.0}) + "\n")
    return run, raw["name"]


def test_driver_records_and_u3_cpu(tmp_path):
    run, lane = _run(tmp_path)
    out = tmp_path / "ev"
    assert SPE.main(["--runs-glob", str(tmp_path / "runs" / "*"), "--u3-lane", lane,
                     "--out", str(out)]) == 0
    s = json.loads((out / "SUMMARY.json").read_text())
    assert s["runs"] == 1 and s["record_shadow"]["counts"].get("agree") == 1
    u3 = json.loads((out / "u3_cpu.json").read_text())[lane]
    assert u3["design_hash"] == "h1" and len(u3["variants"]) == 8
    bad = {k for k, v in u3["variants"].items() if not v["ok"]}
    # vt_480 puts the INNER mouth at 480 mm, so the build box (+ 2 x 3 mm wall) is 6 mm over a
    # 480 mm brief: the envelope-convention decision (senior review §4.2) made concrete.
    assert bad <= {"vt_480"}
    if bad:
        assert u3["variants"]["vt_480"]["envelope_margins_mm"]["height_mm"] == pytest.approx(-6.0)


def test_best_design_picks_lowest_ok_objective(tmp_path):
    run, lane = _run(tmp_path)
    (run / "designs" / "h2").mkdir()
    with (run / "search.ndjson").open("a") as f:
        f.write(json.dumps({"design_hash": "h2", "ok": True, "objective": 2.0}) + "\n")
        f.write(json.dumps({"design_hash": "h3", "ok": True, "objective": 1.0}) + "\n")  # no dir
    assert SPE.best_design([run], lane)[1:] == ("h2", 2.0)
