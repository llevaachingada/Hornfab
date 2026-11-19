"""WP 1.4/1.5 (2026-11-17): rescore tool and frequency noise-floor statistics."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from tools.analysis import rescore_identity as RI

ROOT = Path(__file__).resolve().parents[1]


def test_floor_stats_known_values():
    rng = np.random.default_rng(1)
    v = np.linspace(1.0, 10.0, 40)
    s = v + rng.normal(0.0, 0.1, v.size)
    out = RI.floor_stats(list(zip(s, v)), top=10)
    assert out["n_pairs"] == 40 and out["top"] == 10
    assert out["sd_diff_all"] == pytest.approx(np.std(s - v, ddof=1))
    order = np.argsort(v)[:10]
    assert out["sd_diff_top"] == pytest.approx(np.std((s - v)[order], ddof=1))
    assert out["spearman_all"] > 0.99


def test_floor_stats_drops_missing_and_nonfinite():
    out = RI.floor_stats([(1.0, None), (float("nan"), 2.0), (1.0, 1.1), (2.0, 2.2), (3.0, 2.9)], top=2)
    assert out["n_pairs"] == 3 and out["top"] == 2


def test_rescore_reports_unscorable_designs_instead_of_hiding_them(tmp_path):
    src = ROOT / "examples" / "typologies" / "hypex.yaml"
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    brief = (src.parent / raw["brief_file"]).resolve()
    raw["brief_file"] = str(brief)
    run = tmp_path / "r1"
    (run / "designs" / "abc").mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    (run / "designs" / "abc" / "design.json").write_text(json.dumps({"family": "FREEFORM", "params": {}}))
    s = RI.rescore([run], str(brief), tmp_path / "out")
    assert s["n"] == 1 and s["scored"] == 0 and s["lane_best"] == {}
    row = json.loads((tmp_path / "out" / "rescore.jsonl").read_text().splitlines()[0])
    assert row["design_hash"] == "abc" and row["status"] != "exact_complete"


def test_run_path_keeps_nested_study_runs_locatable(tmp_path):
    """F8 (score-term audit 2026-11-19): a nested run's leaf name ("screen") is not unique."""
    nested = tmp_path / "runs" / "study-abc" / "screen"
    nested.mkdir(parents=True)
    assert RI._run_path(nested) == "study-abc/screen"
    assert RI._run_path(tmp_path / "runs" / "20261116T130335Z-screen-ab4fb9") == "20261116T130335Z-screen-ab4fb9"
    assert RI._run_path(tmp_path / "elsewhere").endswith("elsewhere")
