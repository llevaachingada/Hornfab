"""Overview phase 4 (WP4.3): per-line bounds/params and box-limited flags (headless, offline)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yaml

from hornlab_search.gui import data_overview as O
from hornlab_search.gui import data_overview_params as P


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    reg = {"schema": "score_identities_v1", "updated": "2026-11-19",
           "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
           "identities": [{"id": "home_v10", "label": "Home v10", "brief": "home_v10",
                           "objective_version": 10, "floor_j": 0.5, "status": "current"}]}
    (root / "examples" / "score_identities.yaml").write_text(yaml.safe_dump(reg), encoding="utf-8")
    return root, runs


def _run(runs: Path, rid: str, name: str, bounds: dict, rows: list[dict]) -> Path:
    d = runs / rid
    d.mkdir()
    (d / "config.yaml").write_text(yaml.safe_dump(
        {"name": name, "family": "OSSE", "brief": {"name": "home_v10"},
         "objective": {"version": 10}, "bounds": bounds}), encoding="utf-8")
    out = []
    for i, r in enumerate(rows):
        out.append({"n": i, "design_hash": f"{i:012x}", "ok": True, "mode": "screen",
                    "family": "OSSE", "objective": r["objective"], "params": r["params"],
                    "created_utc": _ts(60 - i)})
    (d / "search.ndjson").write_text("\n".join(json.dumps(x) for x in out) + "\n", encoding="utf-8")
    return d


def _tree(tmp_path: Path):
    root, runs = _repo(tmp_path)
    bounds = {"r0_mm": {"lo": 17.78, "hi": 17.78, "search": False},
              "a_deg": {"lo": 25.0, "hi": 55.0},
              "L_mm": {"lo": 140.0, "hi": 420.0},
              "q": {"lo": 0.9, "hi": 1.0}}
    _run(runs, "20261119T120000Z-screen-aaaaaa", "hl__fold_warm", bounds,
         [{"objective": 2.0, "params": {"r0_mm": 17.78, "a_deg": 40.3, "L_mm": 260.0, "q": 0.955}},
          {"objective": 1.5, "params": {"r0_mm": 17.78, "a_deg": 33.0, "L_mm": 300.0, "q": 0.97}},
          {"objective": 1.0, "params": {"r0_mm": 17.78, "a_deg": 25.0, "L_mm": 260.0, "q": 1.0}}])
    return root, runs


def test_fixed_free_and_bound_hits(tmp_path):
    root, runs = _tree(tmp_path)
    ov = O.overview(root, runs, days=2)
    line = next(l for l in ov["identities"][0]["lines"] if l.get("rank"))
    out = P.line_params(runs, line)
    assert out["error"] is None and out["best_j"] == 1.0
    assert [k["key"] for k in out["fixed"]] == ["r0_mm"]          # search: false listed separately
    assert {k["key"] for k in out["free"]} == {"a_deg", "L_mm", "q"}
    assert out["at_bound"] == ["a_deg", "q"]                      # a_deg at lo, q at hi
    by = {k["key"]: k for k in out["free"]}
    assert by["a_deg"]["at_bound"] == "lo" and by["q"]["at_bound"] == "hi"
    assert by["L_mm"]["at_bound"] is None


def test_two_percent_tolerance_is_inclusive(tmp_path):
    bounds = {"x": {"lo": 0.0, "hi": 100.0}}
    fixed, free, at = P._knobs(bounds, {"x": 2.0})                # exactly 2 % of the span
    assert at == ["x"] and free[0]["at_bound"] == "lo"
    fixed, free, at = P._knobs(bounds, {"x": 2.01})                # just outside
    assert at == [] and free[0]["at_bound"] is None
    fixed, free, at = P._knobs(bounds, {"x": 98.0})
    assert at == ["x"] and free[0]["at_bound"] == "hi"


def test_missing_config_reports_without_raising(tmp_path):
    root, runs = _tree(tmp_path)
    line = {"best_run_id": "20261119T129999Z-screen-ffffff", "construction": "fold",
            "best_j": 1.0}
    out = P.line_params(runs, line)
    assert out["error"] and out["free"] == [] and out["fixed"] == []


def test_params_payload_is_per_ranked_line(tmp_path):
    root, runs = _tree(tmp_path)
    d = P.params(root, runs, days=2)
    ident = d["identities"][0]
    assert ident["id"] == "home_v10" and len(ident["lines"]) == 1
    assert ident["n_bound_lines"] == 1
    assert ident["lines"][0]["best_run_id"] == "20261119T120000Z-screen-aaaaaa"
    # a probe never appears: the payload only carries ranked lines
    assert all(ln.get("best_run_id") for ln in ident["lines"])
