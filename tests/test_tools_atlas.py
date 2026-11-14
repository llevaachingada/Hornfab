"""Offline tests for tools/atlas/build_atlas.py (project atlas page)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_atlas", REPO / "tools" / "atlas" / "build_atlas.py")
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


def _row(n, j, *, ok=True, kind="", cached=False, t="2026-11-01T00:00:00Z", h=None):
    return {"n": n, "ok": ok, "kind": kind, "cached": cached, "objective": j if ok else 1000.0,
            "design_hash": h or f"d{n:04d}", "solve_hash": "s", "created_utc": t, "n_dof": 4000,
            "seconds": {"total": 30.0}, "bbox_m": [0, 0, 0, 0.1, 0.05, 0.2],
            "metrics": {"bw_h_deg": [90, 80], "bw_v_deg": [60, 50], "di_db": [8, 10]}}


def _run(root: Path, rid: str, rows, *, seed=1, mode="screen", algo="cma", config="line_a", ov=7):
    d = root / rid
    d.mkdir(parents=True)
    meta = {"run_id": rid, "mode": mode, "family": "OSSE", "objective_version": ov, "cma_seed": seed,
            "config_name": f"{config}_seed{seed}", "status": "finished", "created_utc": "2026-11-01T00:00:00Z",
            "lib_shas": {"hornlab_beat_bem": "38e5b1f8abc"},
            "config": {"brief": {"name": "brief_x"}, "search": {"algorithm": algo}}}
    (d / "run.json").write_text(json.dumps(meta), encoding="utf-8")
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n{broken", encoding="utf-8")
    return d


@pytest.fixture()
def runs(tmp_path):
    root = tmp_path / "runs"
    rows1 = [_row(i, 10 - i * 0.05) for i in range(60)] + [_row(60, 0, ok=False, kind="invalid_geometry"),
                                                           _row(61, 7.0, cached=True)]
    rows2 = [_row(i, 10 - i * 0.049) for i in range(60)]
    _run(root, "20261101T000000Z-screen-aaaaaa", rows1, seed=1)
    _run(root, "20261102T000000Z-screen-bbbbbb", rows2, seed=2)
    _run(root, "20261103T000000Z-verify-cccccc", [_row(0, 7.5, h="d0059")], mode="verify")
    return root


def test_totals_count_new_solves_and_refusals(runs):
    data = atlas.build(runs)
    t = data["totals"]
    assert t["runs"] == 3
    assert t["solved"] == 121  # 60 + 60 + 1 verify; the cached replay is not a solve
    assert t["refused"] == 1
    assert data["runs"][0]["ref"] == {"invalid_geometry": 1}
    assert data["runs"][0]["pin"] == "38e5b1f"


def test_seeds_group_into_one_line_and_screen_verify_pairs(runs):
    data = atlas.build(runs)
    screen_groups = [g for g in data["groups"]]
    assert len(screen_groups) == 1  # both seeds of line_a on brief_x
    g = screen_groups[0]
    assert g["line"] == "line_a" and g["seeds"] == 2 and g["n_runs"] == 2
    assert g["spread_pct"] is not None
    assert data["fid"] and data["fid"][0][1] == 7.5  # verify J paired with the screen J of d0059


def test_normalised_curve_is_monotone_and_starts_at_one(runs):
    r = atlas.build(runs)["runs"][0]
    assert r["norm"][0] == 1.0
    assert all(a >= b for a, b in zip(r["norm"], r["norm"][1:]))
    assert r["late"] is not None and r["late"] > 0  # still improving in the last 20 %
    assert "lean_in" in atlas.build(runs)["groups"][0]["tags"]


def test_write_embeds_data_and_is_strict_json(runs, tmp_path):
    data = atlas.build(runs)
    page = atlas.write(tmp_path / "out", data, with_json=True)
    html = page.read_text(encoding="utf-8")
    assert "/*__ATLAS_DATA__*/null" not in html
    assert '"generated_utc"' in html
    json.loads((tmp_path / "out" / "atlas.json").read_text(encoding="utf-8"))
