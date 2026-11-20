"""Overview phases 2-4 API routes (``server.App``) on a synthetic repo.

Headless and offline: no solver, no GPU. Guards the one integration seam the phase modules cannot
test alone -- the route table, the findings+health join, the state merge and the snapshot listing.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yaml

from hornlab_search.gui.server import App


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    (root / "docs" / "registry").mkdir(parents=True)
    reg = {"schema": "score_identities_v1", "updated": "2026-11-19",
           "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
           "identities": [{"id": "home_v10", "label": "Home v10", "brief": "home_v10",
                           "objective_version": 10, "floor_j": 0.5, "status": "current"}]}
    (root / "examples" / "score_identities.yaml").write_text(yaml.safe_dump(reg), encoding="utf-8")
    (root / "docs" / "registry" / "project_readiness.yaml").write_text(yaml.safe_dump({
        "schema": "project_readiness_v1", "updated": "2026-11-19",
        "risks": [{"id": "S1", "area": "search", "level": "HIGH", "title": "synthetic",
                   "status": "open", "source": "test"}],
        "decisions": [{"id": "O1", "area": "gui", "question": "q", "recommendation": "r",
                       "status": "decided", "source": "test"}]}), encoding="utf-8")
    return root, runs


def _run(runs: Path, rid: str, name: str, js: list[float], hours_ago: float = 1) -> Path:
    d = runs / rid
    d.mkdir()
    (d / "config.yaml").write_text(yaml.safe_dump(
        {"name": name, "family": "OSSE", "brief": {"name": "home_v10"},
         "objective": {"version": 10},
         "bounds": {"a_deg": {"lo": 25.0, "hi": 55.0},
                    "r0_mm": {"lo": 17.78, "hi": 17.78, "search": False}}}), encoding="utf-8")
    rows = [{"n": i, "design_hash": f"{i:012x}", "ok": True, "mode": "screen", "family": "OSSE",
             "objective": j, "params": {"a_deg": 25.0 if i == 2 else 40.0 + i, "r0_mm": 17.78},
             "failures": {},
             "created_utc": _ts(hours_ago * 60 - i)} for i, j in enumerate(js)]
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return d


def _app(tmp_path: Path) -> App:
    root, runs = _repo(tmp_path)
    _run(runs, "20261119T120000Z-screen-aaaaaa", "hl__fold_warm", [3.0, 2.0, 1.0])
    _run(runs, "20261119T120001Z-screen-bbbbbb", "hl__morph", [1.2, 1.1, 1.05])
    return App(root, runs)


def test_findings_route_joins_health_and_merges_state(tmp_path):
    a = _app(tmp_path)
    out = a._get_uncoalesced("/api/overview/findings", {"days": ["2"]})
    assert out["findings"] and set(out["counts"]) == {"critical", "high", "medium", "low"}
    kinds = {f["kind"] for f in out["findings"]}
    # the two morph/fold lines are within floor 0.5 -> one tie_verify
    assert "tie_verify" in kinds
    # every finding names at most one identity (software findings may name none), and the rankable
    # lines of this fixture are all in home_v10
    assert all(isinstance(f["identity_id"], str) for f in out["findings"])
    assert all(f["identity_id"] == "home_v10" for f in out["findings"] if f["kind"] != "software")
    ids = [f["id"] for f in out["findings"]]
    assert len(ids) == len(set(ids))
    # a dismiss survives the GET (state merge) but a computed resolved does not get overridden
    target = next(f for f in out["findings"] if f["kind"] == "tie_verify")
    assert a.post(f"/api/overview/findings/{target['id']}", {"status": "acknowledged"})["ok"]
    again = a._get_uncoalesced("/api/overview/findings", {"days": ["2"]})
    assert next(f for f in again["findings"] if f["id"] == target["id"])["status"] == "acknowledged"
    assert a.post(f"/api/overview/findings/{target['id']}", {"status": "open"})["ok"]


def test_findings_route_rejects_bad_days(tmp_path):
    a = _app(tmp_path)
    for bad in ("0", "400", "x"):
        try:
            a._get_uncoalesced("/api/overview/findings", {"days": [bad]})
        except (ValueError, TypeError):
            continue
        raise AssertionError(f"days={bad!r} was accepted")


def test_registry_health_params_snapshots_routes(tmp_path):
    a = _app(tmp_path)
    reg = a._get_uncoalesced("/api/overview/registry", {})
    assert reg["counts"]["total"] == 2
    assert {r["area"] for r in reg["risks"]} == {"search"}
    # the synthetic tree has no HW readiness file: the loader reports that, never drops it silently
    assert any("system_woofer_2026-11-18" in e for e in reg["errors"])

    health = a._get_uncoalesced("/api/overview/health", {"days": ["2"]})
    assert isinstance(health["findings"], list)

    pr = a._get_uncoalesced("/api/overview/params", {"days": ["2"]})
    ident = pr["identities"][0]
    assert ident["id"] == "home_v10" and len(ident["lines"]) == 2
    line = next(l for l in ident["lines"] if l["construction"] == "fold")
    assert [k["key"] for k in line["fixed"]] == ["r0_mm"]
    assert line["at_bound"] == ["a_deg"]           # 25.0 is the lower bound
    assert a._get_uncoalesced("/api/overview/snapshots", {}) == {"snapshots": []}


def test_post_rejects_an_unknown_status(tmp_path):
    a = _app(tmp_path)
    fid = a._get_uncoalesced("/api/overview/findings", {"days": ["2"]})["findings"][0]["id"]
    try:
        a.post(f"/api/overview/findings/{fid}", {"status": "bogus"})
    except ValueError as exc:
        assert "status" in str(exc)
    else:                                          # pragma: no cover
        raise AssertionError("a bogus status was accepted")
