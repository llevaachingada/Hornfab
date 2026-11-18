"""WP 3.3/3.4 (2026-11-17): record shadow gate over a synthetic run dir."""
import json
from pathlib import Path

import yaml

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from tools.analysis import record_shadow as RS

ROOT = Path(__file__).resolve().parents[1]


def _run_dir(tmp_path):
    src = ROOT / "examples" / "typologies" / "hypex.yaml"
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    raw["brief_file"] = str((src.parent / raw["brief_file"]).resolve())
    run = tmp_path / "run1"
    (run / "designs").mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(run / "config.yaml")
    space = DesignSpace.from_config(cfg)
    seed = space.seed
    knobs = dict(space.seed_knobs)
    rows = []
    # 1: the seed, solved ok
    (run / "designs" / "a").mkdir()
    (run / "designs" / "a" / "design.json").write_text(json.dumps(
        {"family": seed.family, "params": seed.params, "design_hash": "a"}, default=float))
    rows.append({"design_hash": "a", "ok": True, "kind": ""})
    # 2: the same legal knobs, but stored as a pre-mesh envelope refusal -> a false refusal
    (run / "designs" / "b").mkdir()
    (run / "designs" / "b" / "design.json").write_text(json.dumps(
        {"family": "FREEFORM", "design_hash": "b",
         "params": {"_generator_error": "invalid_envelope: estimated outside", "_knobs": knobs}}))
    rows.append({"design_hash": "b", "ok": False, "kind": "invalid_envelope"})
    # 3: a refusal with nothing to rebuild -> record_failed, reported not hidden
    (run / "designs" / "c").mkdir()
    (run / "designs" / "c" / "design.json").write_text(json.dumps(
        {"family": "FREEFORM", "design_hash": "c", "params": {"_generator_error": "x"}}))
    rows.append({"design_hash": "c", "ok": False, "kind": "invalid_geometry"})
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return run


def test_shadow_gate_classifies_and_writes_records(tmp_path):
    run = _run_dir(tmp_path)
    out = tmp_path / "out"
    assert RS.main([str(run), "--out", str(out)]) == 0
    recs = {r["design_hash"]: r for r in map(json.loads, (out / "records.jsonl").read_text().splitlines())}
    assert recs["a"]["shadow"] == "agree" and recs["a"]["route"] == "native"
    assert len(recs["a"]["record_digest"]) == 64
    assert recs["b"]["shadow"] == "record_inside_but_refused" and recs["b"]["how"] == "rematerialised"
    assert recs["c"]["shadow"] == "record_failed" and "error" in recs["c"]
    summary = json.loads((out / "summary.json").read_text())
    assert summary["counts"] == {"agree": 1, "record_inside_but_refused": 1, "record_failed": 1}


def test_classify_rules():
    assert RS.classify("invalid_envelope", False, {"width_mm": 2.0}) == "record_inside_but_refused"
    assert RS.classify("", True, {"width_mm": -3.0}) == "record_outside_but_ok"
    assert RS.classify("invalid_envelope", False, {"width_mm": -3.0}) == "agree"
    assert RS.classify("", True, {"width_mm": -0.2}) == "agree"         # within 0.5 mm tolerance
