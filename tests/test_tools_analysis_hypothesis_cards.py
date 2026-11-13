"""Source-backed parent identities, legal construction and required ablations."""
import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from test_tools_analysis_common import load_tool

hc = load_tool("hypothesis_cards")
REPO = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    parents = []
    configs = []
    for i in range(3):
        raw = yaml.safe_load((REPO / "examples/osse_baseline.yaml").read_text())
        raw["seed_params"]["L_mm"] = 240 + i * 20
        path = tmp_path / f"p{i}.yaml"
        path.write_text(yaml.safe_dump(raw))
        d = DesignSpace.from_config(load_config(path)).seed
        source = tmp_path / f"parent{i}.json"
        source.write_text(json.dumps({"family": d.family, "params": d.params, "design_hash": d.hash()}))
        if i < 2:
            parents.append({"id": d.hash(), "design_hash": d.hash(), "source": str(source)})
        configs.append(str(path))
    return {"identity": {"task_id": "task", "scoring_context_id": "score", "physical_spec_id": "spec", "objective_version": 1},
            "parents": parents, "expected_band_hz": [700, 5000], "trade_off": "coverage versus loading",
            "features": ["mouth profile"], "unknowns": ["mesh sensitivity"], "constraints": ["driver throat held"],
            "experiments": [{"role": role, "config": configs[2 if role == "combination" else (1 if role == "parent_b" else 0)],
                             "removed_feature": "mouth profile" if role.startswith("ablate") else None,
                             "parent_ids": [p["id"] for p in parents]}
                            for role in sorted(hc.ROLES)]}


def test_card_roundtrip_and_markdown(tmp_path):
    spec = fixture(tmp_path)
    card = hc.build_card(spec, base=tmp_path)
    assert hc.build_card(spec, base=tmp_path) == card
    assert card["status"] == "proposed"
    assert all(p["id"] in hc.markdown(card) for p in card["parents"])
    assert set(e["role"] for e in card["experiments"]) == hc.ROLES
    assert hc.main(["--spec", str(write_spec(tmp_path, spec)), "--out", str(tmp_path / "out")]) == 0
    assert json.loads((tmp_path / "out/hypothesis_cards.json").read_text())["card_id"] == card["card_id"]


def write_spec(tmp_path, spec):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return path


@pytest.mark.parametrize("fault", ["fake_id", "bad_hash", "no_ablation", "bad_band", "wrong_parent", "meh",
                                 "context_drift", "objective_drift", "duplicate_combo", "empty_ablation"])
def test_refuse_invented_or_incomplete_cards(tmp_path, fault):
    spec = fixture(tmp_path)
    if fault == "fake_id":
        spec["parents"][0]["id"] = "invented"
    elif fault == "bad_hash":
        spec["parents"][0]["design_hash"] = "wrong"
    elif fault == "no_ablation":
        spec["experiments"] = [e for e in spec["experiments"] if e["role"] != "ablate_a"]
    elif fault == "bad_band":
        spec["expected_band_hz"] = [5000, 700]
    elif fault == "wrong_parent":
        next(e for e in spec["experiments"] if e["role"] == "parent_b")["config"] = str(tmp_path / "p0.yaml")
    elif fault == "meh":
        path = Path(spec["parents"][0]["source"])
        raw = json.loads(path.read_text())
        raw["family"] = "MEH"
        path.write_text(json.dumps(raw))
    elif fault == "context_drift":
        path = tmp_path / "p2.yaml"
        raw = yaml.safe_load(path.read_text())
        raw["weights"]["cov"] = 2.0
        path.write_text(yaml.safe_dump(raw))
    elif fault == "objective_drift":
        spec["identity"]["objective_version"] = 4
    elif fault == "duplicate_combo":
        next(e for e in spec["experiments"] if e["role"] == "combination")["config"] = str(tmp_path / "p0.yaml")
    elif fault == "empty_ablation":
        next(e for e in spec["experiments"] if e["role"] == "ablate_a")["removed_feature"] = ""
    with pytest.raises(ValueError):
        hc.build_card(spec, base=tmp_path)
