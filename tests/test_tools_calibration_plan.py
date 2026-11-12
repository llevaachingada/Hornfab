"""Tests for tools/calibration/plan_calibration.py (C.1) -- synthetic, offline, no solves."""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "calibration"))

import plan_calibration as plan  # noqa: E402

from hornlab_search.config import load_config  # noqa: E402  (worktree package via pythonpath = ["."])

DAY = "2026-11-12"
HASH_A = "aaaaaaaaaaaaaaaa"
HASH_B = "bbbbbbbbbbbbbbbb"


def _write_row(handle, n: int, design: str, objective: float, ok: bool = True) -> None:
    handle.write(json.dumps({
        "n": n, "mode": "screen", "design_hash": design, "family": "OSSE",
        "params": {"L_mm": 260.0 + n}, "objective": objective, "ok": ok,
        "error": "" if ok else "invalid_geometry: no",
    }, allow_nan=False, separators=(",", ":")) + "\n")


@pytest.fixture()
def repo(tmp_path):
    """A fake repo root: examples/ exists, one source run dir with a real config snapshot."""
    (tmp_path / "examples").mkdir()
    run_dir = tmp_path / "runs" / "20261112T010101Z-screen-abcdef"
    run_dir.mkdir(parents=True)
    shutil.copy(REPO / "examples" / "osse_baseline.yaml", run_dir / "config.yaml")
    with open(run_dir / "search.ndjson", "w", encoding="utf-8", newline="\n") as fh:
        # 3 designs, one with a duplicate better row and one refused row.
        _write_row(fh, 1, HASH_A, 0.9)
        _write_row(fh, 2, HASH_A, 0.7)      # duplicate: the better J wins
        _write_row(fh, 3, HASH_B, 0.8)
        _write_row(fh, 4, "cccccccccccccccc", 0.6, ok=False)   # refused: never selected
    return tmp_path


def test_plan_generates_night_overlays_and_variant_dirs(repo):
    out = repo / "runs" / "nights" / f"calibration_{DAY}.yaml"
    (out.parent).mkdir()
    summary = plan.plan_calibration(
        designs=plan._load_designs([str(repo / "runs" / "20261112T010101Z-screen-abcdef")],
                                   20, repo),
        top=20, out=out, repo_root=repo, date=DAY,
        variants_dir=repo / "scratch" / f"calibration_{DAY}" / "variants")
    assert summary["jobs"] == 6  # 6 variants x 1 run
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["night"] == f"calibration_{DAY}"
    assert [j["kind"] for j in doc["jobs"]] == ["command"] * 6
    # runner-format sanity: the runner's own validator must accept the generated file
    sys.path.insert(0, str(REPO / "tools"))
    from run_campaign_night import load_night  # noqa: E402  (worktree runner)
    loaded = load_night(out)
    assert loaded.night == f"calibration_{DAY}" and len(loaded.jobs) == 6
    argv = next(j.argv for j in loaded.jobs if j.id.startswith("c_band_split__"))
    assert argv[:3] == (".venv/Scripts/hornlab-search.exe", "verify", "--run")
    assert "verify" in str(argv) and "--designs" in argv
    wanted = argv[argv.index("--designs") + 1].split(",")
    assert wanted == [HASH_A, HASH_B]
    # metadata block survives (the runner ignores it; compare_calibration.py reads it)
    meta = doc["calibration"]
    assert meta["thresholds"] == plan.THRESHOLDS
    assert meta["aspect_pairs"]["mesh_policy"] == ["band_split", "single_mesh"]
    assert meta["designs"][0]["hash"] == HASH_A
    assert meta["runs"][str(repo / "runs" / "20261112T010101Z-screen-abcdef")] \
        ["band_lo_hz"] == 700.0


def test_overlays_use_extends_and_variant_configs_load(repo):
    run_dir = repo / "runs" / "20261112T010101Z-screen-abcdef"
    plan.plan_calibration(
        designs=plan._load_designs([str(run_dir)], 20, repo),
        top=20, out=repo / "n.yaml", repo_root=repo, date=DAY,
        variants_dir=repo / "scratch" / "v")
    overlays = sorted((repo / "examples" / "calibration" / DAY).glob("*.yaml"))
    # 5 overriding variants + the per-run new-screen-grid proposal
    assert len(overlays) == 6
    band = (repo / "examples" / "calibration" / DAY / "20261112T010101Z-screen-abcdef__band_split.yaml")
    text = band.read_text(encoding="utf-8")
    assert "extends:" in text
    doc = yaml.safe_load(text)
    assert doc["mesh"]["band_split"]["edges_hz"] == [2000.0]
    # every materialized variant config loads through the repo's own loader,
    # and the override is really present in the loaded Config
    vdir = repo / "scratch" / "v" / "20261112T010101Z-screen-abcdef__band_split"
    cfg = load_config(vdir / "config.yaml")
    assert cfg.mesh.band_split == {"edges_hz": [2000.0]}
    assert cfg.target_raw["band_lo_hz"] == 700.0          # the brief/target chain survived
    for variant in ("dist_2m", "dist_10m", "epw_6", "epw_9", "single_mesh"):
        load_config(vdir.parent / f"20261112T010101Z-screen-abcdef__{variant}" / "config.yaml")
    cfg2 = load_config(vdir.parent / "20261112T010101Z-screen-abcdef__dist_10m" / "config.yaml")
    assert cfg2.solve.distance_m == 10.0
    cfg3 = load_config(vdir.parent / "20261112T010101Z-screen-abcdef__epw_9" / "config.yaml")
    assert cfg3.mesh.epw == 9.0
    # control variant: pure chain, no override
    cfg4 = load_config(vdir.parent / "20261112T010101Z-screen-abcdef__single_mesh" / "config.yaml")
    assert cfg4.mesh.band_split is None and cfg4.solve.distance_m == 2.0
    # filtered ndjson holds only the selected hashes and keeps the better duplicate
    rows = [json.loads(l) for l in
            (vdir / "search.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert {r["design_hash"] for r in rows} == {HASH_A, HASH_B}
    assert len(rows) == 3
    assert any(r["objective"] == 0.7 for r in rows)
    # provenance run.json
    assert json.loads((vdir / "run.json").read_text(encoding="utf-8"))["variant"] == "band_split"


def test_band_split_edge_outside_band_is_refused_at_plan_time(repo, tmp_path):
    run_dir = repo / "runs" / "20261112T010101Z-screen-abcdef"
    cfg = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
    cfg["target"]["band_hi_hz"] = 1500.0     # 2 kHz no longer inside the band
    run_dir2 = repo / "runs" / "narrow"
    run_dir2.mkdir(parents=True)
    (run_dir2 / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    shutil.copy(run_dir / "search.ndjson", run_dir2 / "search.ndjson")
    with pytest.raises(plan.PlanError, match="preflight failed"):
        plan.plan_calibration(designs=plan._load_designs([str(run_dir2)], 20, repo),
                              top=20, out=repo / "n2.yaml", repo_root=repo, date=DAY,
                              variants_dir=repo / "scratch" / "v2")


def test_top_selection_dedup_and_refusals(repo, capsys):
    out = repo / "runs" / "nights"
    out.mkdir()
    rc = plan.main(["--designs", str(repo / "runs" / "20261112T010101Z-screen-abcdef"),
                    "--top", "1", "--out", str(out / "x.yaml"),
                    "--repo-root", str(repo), "--date", DAY,
                    "--variants-dir", str(repo / "scratch" / "top1")])
    assert rc == 0
    doc = yaml.safe_load((out / "x.yaml").read_text(encoding="utf-8"))
    assert doc["calibration"]["designs"][0]["hash"] == HASH_A   # top 1: J 0.7 wins over 0.8
    argv = doc["jobs"][0]["argv"]
    assert argv[argv.index("--designs") + 1] == HASH_A


def test_csv_input_with_run_column(repo):
    run_dir = repo / "runs" / "20261112T010101Z-screen-abcdef"
    csv_path = repo / "finalists.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["design", "run"])
        writer.writeheader()
        writer.writerow({"design": HASH_B, "run": str(run_dir)})
        writer.writerow({"design": HASH_A, "run": str(run_dir)})
    designs = plan._load_designs([str(csv_path)], 20, repo)
    hashes = [e["hash"] for e in designs[str(run_dir)]]
    assert hashes == [HASH_A, HASH_B]                    # sorted, both kept
    assert designs[str(run_dir)][0]["screen_j"] == 0.7   # J filled from the run's rows


def test_csv_hash_absent_from_run_errors(repo):
    csv_path = repo / "bad.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["design", "run"])
        writer.writeheader()
        writer.writerow({"design": "deaddeaddeaddead", "run":
                         str(repo / "runs" / "20261112T010101Z-screen-abcdef")})
    with pytest.raises(plan.PlanError, match="no ok row"):
        plan._load_designs([str(csv_path)], 20, repo)


def test_new_screen_grid_proposal_overlay(repo):
    run_dir = repo / "runs" / "20261112T010101Z-screen-abcdef"
    plan.plan_calibration(designs=plan._load_designs([str(run_dir)], 20, repo),
                          top=20, out=repo / "n3.yaml", repo_root=repo, date=DAY,
                          variants_dir=repo / "scratch" / "v3")
    overlay = repo / "examples" / "calibration" / DAY / \
        "20261112T010101Z-screen-abcdef__new_screen_grid.yaml"
    text = overlay.read_text(encoding="utf-8")
    assert "PROPOSAL ONLY" in text
    doc = yaml.safe_load(text)
    assert doc["mesh"]["band_split"]["edges_hz"] == [2000.0]
    grid = doc["solve"]["freq_grid"]
    assert grid["lo_hz"] == 700.0 and grid["hi_hz"] == 5500.0
    assert grid["points_per_octave"] == 6.0
    cfg = load_config(overlay)          # the proposal must itself be loadable
    assert cfg.mesh.band_split is not None
    # ... and it must NOT be a night job
    doc_night = yaml.safe_load((repo / "n3.yaml").read_text(encoding="utf-8"))
    assert all("__new_screen_grid" not in j["id"] for j in doc_night["jobs"])


def test_list_only_writes_nothing(repo, capsys):
    rc = plan.main(["--designs", str(repo / "runs" / "20261112T010101Z-screen-abcdef"),
                    "--out", str(repo / "list.yaml"), "--repo-root", str(repo),
                    "--date", DAY, "--list-only"])
    assert rc == 0
    assert not (repo / "list.yaml").exists()
    text = capsys.readouterr().out
    assert HASH_A in text and HASH_B in text
