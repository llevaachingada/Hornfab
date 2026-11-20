"""Offline tests for tools/night_queue/mirror_bo_studies.py (BO study solves -> CMA-shaped run folder)."""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("mirror_bo_studies", REPO / "tools/night_queue/mirror_bo_studies.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

PKG = "48298edcdb4292b318effa459e6fff07adcc60ed62c4203b4f665aa3a70f12f5"


def _row(n, h, j, ok=True, mode="screen"):
    return {"n": n, "design_hash": h, "objective": j, "ok": ok, "mode": mode, "family": "OSSE",
            "params": {"a": n}, "terms": {"total": j}, "objective_version": 7,
            "created_utc": f"2026-11-16T18:0{n}:00Z"}


def _study(runs: Path, rows, verify_rows=None, policy="turbo", seed=85003):
    study = runs / f"study-{PKG[:16]}"
    scr = study / "screen"
    for r in rows:
        d = scr / "designs" / r["design_hash"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "mesh.msh").write_text("mesh " + r["design_hash"])
        (d / "metrics.json").write_text("{}")
    (scr / "search.ndjson").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (scr / "config.yaml").write_text("name: hl__x_v8\nbrief_file: b.yaml\n")
    (scr / "run.json").write_text(json.dumps({"mode": "screen", "name": "hl__x_v8",
                                              "started_utc": "2026-11-16T18:03:35.305672+00:00"}))
    if verify_rows:
        v = study / "verify"
        v.mkdir(parents=True)
        (v / "search.ndjson").write_text("".join(json.dumps(r) + "\n" for r in verify_rows))
        (v / "run.json").write_text(json.dumps({"mode": "verify"}))
    arm = runs / "night_x" / "turbo_arm"
    arm.mkdir(parents=True)
    (arm / "package.json").write_text(json.dumps({"package_id": PKG, "budget": {"screen_calls": 80}}) + "\n")
    con = sqlite3.connect(arm / "studies.sqlite3")
    con.execute("create table revisions (study_id text, revision int, spec_json text, spec_hash text)")
    con.execute("insert into revisions values ('s', 1, ?, 'h')",
                (json.dumps({"policy": {"proposal_policy": policy, "seed": seed}}),))
    con.commit()
    con.close()
    return study


def test_mirror_is_a_cma_shaped_run_with_hard_links(tmp_path):
    runs = tmp_path / "runs"
    study = _study(runs, [_row(0, "aaaaaaaaaaaa", 5.0), _row(1, "bbbbbbbbbbbb", 4.1),
                          _row(2, "cccccccccccc", 900.0, ok=False)],
                   verify_rows=[_row(0, "bbbbbbbbbbbb", 4.3, mode="verify")])
    assert M.main(["--runs", str(runs)]) == 0
    mirror = runs / "20261116T180335Z-turbo-48298e"
    assert mirror.is_dir()
    # GUI's RUN_ID pattern accepts the name
    from hornlab_search.gui import data as D
    assert D.RUN_ID.match(mirror.name)
    # same files a CMA run has, as hard links (no copy)
    for rel in ("search.ndjson", "config.yaml", "designs/bbbbbbbbbbbb/mesh.msh", "verify/search.ndjson"):
        assert os.path.samefile(mirror / rel, (study / "screen" / rel) if not rel.startswith("verify")
                                else study / rel)
    rj = json.loads((mirror / "run.json").read_text())
    assert rj["algorithm"] == "turbo" and rj["bo_seed"] == 85003 and "--cma-seed 85003" in rj["command"]
    best = json.loads((mirror / "best.json").read_text())
    assert best["design_hash"] == "bbbbbbbbbbbb" and best["objective"] == pytest.approx(4.1)
    # the GUI summary sees it like any run, labelled with its optimizer
    s = D.run_summary(mirror)
    assert s["algorithm"] == "turbo" and s["best_j"] == pytest.approx(4.1) and s["n"] == 3
    assert s["has_inline_verify"] is True and s["cma_seed"] == 85003


def test_mirror_is_idempotent_and_picks_up_new_designs(tmp_path):
    runs = tmp_path / "runs"
    study = _study(runs, [_row(0, "aaaaaaaaaaaa", 5.0)])
    M.main(["--runs", str(runs)])
    d = study / "screen" / "designs" / "dddddddddddd"
    d.mkdir()
    (d / "mesh.msh").write_text("new")
    res = M.mirror_one(study, runs, M.arm_index(runs))
    assert res["linked"] == 1  # only the new file
    assert (runs / res["mirror"] / "designs/dddddddddddd/mesh.msh").read_text() == "new"
    assert M.mirror_one(study, runs, M.arm_index(runs))["linked"] == 0


def test_prune_removes_orphan_mirrors_only(tmp_path):
    runs = tmp_path / "runs"
    study = _study(runs, [_row(0, "aaaaaaaaaaaa", 5.0)])
    M.main(["--runs", str(runs)])
    cma = runs / "20261116T000000Z-screen-abcdef"
    cma.mkdir()
    import shutil
    shutil.rmtree(study)
    M.main(["--runs", str(runs), "--prune"])
    assert not (runs / "20261116T180335Z-turbo-48298e").exists()
    assert cma.is_dir()


def test_cma_runs_default_to_cma_algorithm(tmp_path):
    from hornlab_search.gui import data as D
    for suffix, cfg, want in (("abcdef", "name: x\nsearch:\n  algorithm: cma_me\n", "cma_me"),
                              ("abcde0", "name: x\n", "cma")):
        run = tmp_path / f"20261116T000000Z-screen-{suffix}"
        run.mkdir()
        (run / "search.ndjson").write_text(json.dumps(_row(0, "aaaaaaaaaaaa", 3.0)) + "\n")
        (run / "config.yaml").write_text(cfg)
        assert D.run_summary(run)["algorithm"] == want
