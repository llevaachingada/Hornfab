"""Offline tests for ``tools/data/top_designs.py`` (GPU-solve export bundle).

Hermetic: a synthetic ``runs/`` tree with ``run.json``, ``search.ndjson`` and tiny
``response.npz`` files. No GPU, no solver, no real run bytes. The tool is loaded by path,
matching the ``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from conftest import REPO

TOOL = REPO / "tools" / "data" / "top_designs.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("top_designs_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


top_designs = _load_tool()

GEN_OSSE = {"spec": {"name": "typology", "profile_h": {"type": "osse"}}}
GEN_BIRADIAL = {"spec": {"name": "typology", "profile_h": {"type": "biradial"}}}


def _config(*, name="cfg", objective=None, weights=None, target=None, brief_file="brief.yaml"):
    return {
        "name": name,
        "family": "OSSE",
        "brief_file": brief_file,
        "brief": "synthetic test brief",
        "objective": objective if objective is not None else {"version": 7, "tolerances": {"rip": 1.0}},
        "weights": weights if weights is not None else {"rip": 1.0},
        "target": target if target is not None else {"band_lo_hz": 300.0, "band_hi_hz": 8000.0},
    }


def _row(
    design,
    solve,
    *,
    mesh="m1",
    family="OSSE",
    objective=1.0,
    ok=True,
    objective_version=7,
    generator=None,
    params=None,
    terms=None,
    metrics=None,
    backend="beat_cuda",
    lane="gpu",
    mode="screen",
):
    row = {
        "mode": mode,
        "design_hash": design,
        "mesh_hash": mesh,
        "solve_hash": solve,
        "family": family,
        "params": dict(params or {"L_mm": 250.0, "r0_mm": 18.0}),
        "objective": objective,
        "ok": ok,
        "created_utc": "2026-01-01T00:00:00Z",
        "terms": dict(terms or {"rip": 0.5, "flat": 0.25, "total": objective}),
        "metrics": metrics
        if metrics is not None
        else {
            "freqs_hz": [300.0, 1000.0, 3000.0],
            "bw_h_deg": [120.0, 80.0, 50.0],
            "bw_v_deg": [100.0, 70.0, 45.0],
            "di_db": [3.0, 8.0, 12.0],
            "ripple_h_db": [0.5, 0.6, 0.7],
            "ripple_v_db": [0.4, 0.5, 0.6],
            "on_axis_db": [0.0, 1.0, 2.0],
            "z_throat_real": [1.0, 1.0, 1.0],
            "di_source": "balloon",
            "scalars": {"di_mean_db": 8.0, "ripple_mean_db": 0.55, "f11_hz": 6000.0},
        },
        "backend": backend,
        "lane": lane,
        "n_dof": 3000,
        "n_triangles": 6000,
        "quadrants": "1",
        "symmetry_plane": "yz+xz",
        "bbox_m": [0.0, 0.0, 0.0, 0.1, 0.12, 0.2],
        "res_mm": {"throat": 3.0, "mouth": 6.0, "rear": 6.0},
        "peak_vram_mb": 150.0,
        "seconds": {"mesh": 1.0, "solve": 2.0, "total": 3.0},
        "cached": False,
    }
    if objective_version is not None:
        row["objective_version"] = objective_version
    if generator is not None:
        row["generator"] = generator
    return row


def _write_run(
    runs_root: Path,
    name: str,
    rows: list[dict],
    *,
    objective_version=7,
    backend="beat_cuda",
    config=None,
    with_responses=True,
):
    run = runs_root / name
    run.mkdir(parents=True)
    run_json = {
        "run_id": name,
        "config_name": (config or _config())["name"],
        "config_sha": "cfgsha",
        "config_path": "examples/synthetic.yaml",
        "family": "OSSE",
        "backend": backend,
        "objective_version": objective_version,
        "lib_shas": {"hornlab_search": "abc"},
        "created_utc": "2026-01-01T00:00:00Z",
        "mode": "screen",
        "status": "ok",
        "config": config or _config(),
    }
    (run / "run.json").write_text(json.dumps(run_json), encoding="utf-8")
    (run / "search.ndjson").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    if not with_responses:
        return run
    for row in rows:
        if not row.get("ok"):
            continue
        design_dir = run / "designs" / row["design_hash"]
        design_dir.mkdir(parents=True, exist_ok=True)
        np.savez(
            design_dir / "response.npz",
            freqs_hz=np.array([300.0, 1000.0, 3000.0]),
            h_angles_deg=np.array([-90.0, 0.0, 90.0]),
            v_angles_deg=np.array([-90.0, 0.0, 90.0]),
            spl_h_db=np.arange(9.0).reshape(3, 3),
            spl_v_db=np.arange(9.0, 18.0).reshape(3, 3),
            balloon_dirs=np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]),
            spl_balloon_db=np.arange(6.0).reshape(3, 2),
            z_throat=np.array([1.0 + 0.1j, 1.0 + 0.2j, 1.0 + 0.3j]),
        )
        (design_dir / "mesh_meta.json").write_text(
            json.dumps({"summary": {"area_m2": 0.05}}), encoding="utf-8"
        )
    return run


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _run_export(tmp_path: Path, **kwargs):
    runs = tmp_path / "runs"
    out = tmp_path / "out"
    return top_designs.run(runs_root=runs, out_dir=out, **kwargs), out


# --------------------------------------------------------------------------- selection


def test_top_n_per_typology_and_score_set(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_a",
        [
            _row("d1", "s1", objective=3.0, generator=GEN_OSSE),
            _row("d2", "s2", objective=1.0, generator=GEN_OSSE),
            _row("d3", "s3", objective=2.0, generator=GEN_OSSE),
            _row("b1", "s4", objective=5.0, family="FREEFORM", generator=GEN_BIRADIAL),
            _row("b2", "s5", objective=4.0, family="FREEFORM", generator=GEN_BIRADIAL),
        ],
    )
    _write_run(
        runs,
        "run_b",
        [
            _row("d4", "s6", objective=2.0, objective_version=4, generator=GEN_OSSE),
            _row("d5", "s7", objective=1.0, objective_version=4, generator=GEN_OSSE),
        ],
        objective_version=4,
    )

    doc, out = _run_export(tmp_path, top_n=2)
    assert (out / "top_designs.csv").is_file()
    assert (out / "top_designs.json").is_file()
    assert (out / "top_designs_acoustics.npz").is_file()
    assert doc["counts"]["groups"] == 3
    assert doc["counts"]["selected"] == 6

    groups = {group["group_id"]: group for group in doc["groups"]}
    assert groups["OSSE|v7"]["n_selected"] == 2
    assert groups["OSSE|v7"]["design_row_ids"] == [
        "OSSE|v7#01",
        "OSSE|v7#02",
    ]
    assert groups["biradial|v7"]["n_selected"] == 2
    assert groups["OSSE|v4"]["n_selected"] == 2
    assert groups["OSSE|v7"]["n_scored"] == 3

    by_id = {design["row_id"]: design for design in doc["designs"]}
    assert by_id["OSSE|v7#01"]["objective"] == 1.0
    assert by_id["OSSE|v7#02"]["objective"] == 2.0
    assert by_id["OSSE|v4#01"]["objective"] == 1.0


def test_gpu_filter_and_physical_solve_dedupe(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_a",
        [
            _row("gpu1", "s1", objective=2.0, generator=GEN_OSSE),
            # Same physical solve scored twice in one run: lowest J wins.
            _row("gpu1", "s1", objective=1.5, generator=GEN_OSSE),
            _row("cpu1", "s2", objective=0.01, generator=GEN_OSSE, backend="beat_cpu", lane="cpu"),
            _row("gpu2", "s3", objective=3.0, generator=GEN_OSSE),
        ],
    )
    _write_run(
        runs,
        "run_cpu",
        [_row("cpu2", "s4", objective=0.02, generator=GEN_OSSE, backend=None, lane=None)],
        backend="beat_cpu",
    )

    doc, _ = _run_export(tmp_path, top_n=10)
    objectives = sorted(design["objective"] for design in doc["designs"])
    assert objectives == [1.5, 3.0]
    assert doc["counts"]["not_gpu"] == 2


def test_same_physical_solve_is_kept_per_score_set(tmp_path):
    runs = tmp_path / "runs"
    _write_run(runs, "run_v7", [_row("same", "s1", objective=3.0, generator=GEN_OSSE)])
    _write_run(
        runs,
        "run_v4",
        [_row("same", "s1", objective=1.0, objective_version=4, generator=GEN_OSSE)],
        objective_version=4,
    )

    doc, _ = _run_export(tmp_path, top_n=10)
    assert {design["score_set"] for design in doc["designs"]} == {"v7", "v4"}
    assert len(doc["designs"]) == 2
    assert doc["counts"]["unique_scored_solves"] == 2


def test_unversioned_group_and_exclude_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_old",
        [_row("old1", "s1", objective=2.0, objective_version=None, generator=GEN_OSSE)],
        objective_version=None,
    )

    doc, _ = _run_export(tmp_path, top_n=10)
    assert doc["counts"]["groups"] == 1
    assert doc["designs"][0]["score_set"] == "unversioned"
    assert doc["designs"][0]["version_source"] == "missing"

    excluded, _ = _run_export(tmp_path, top_n=10, include_unversioned=False)
    assert excluded["counts"]["groups"] == 0
    assert excluded["counts"]["selected"] == 0


def test_score_config_grouping_splits_same_version(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_a",
        [_row("a1", "s1", objective=1.0, generator=GEN_OSSE)],
        config=_config(name="cfg_a", target={"band_lo_hz": 300.0}),
    )
    _write_run(
        runs,
        "run_b",
        [_row("b1", "s2", objective=1.0, generator=GEN_OSSE)],
        config=_config(name="cfg_b", target={"band_lo_hz": 500.0}),
    )

    by_version, _ = _run_export(tmp_path, top_n=10, group_by="score")
    assert by_version["counts"]["groups"] == 1
    by_config, _ = _run_export(tmp_path, top_n=10, group_by="score-config")
    assert by_config["counts"]["groups"] == 2
    assert all(":" in group["score_set"] for group in by_config["groups"])


def test_archive_trees_are_skipped(tmp_path):
    runs = tmp_path / "runs"
    _write_run(runs, "run_a", [_row("a1", "s1", objective=1.0, generator=GEN_OSSE)])
    archived = runs / "analysis" / "_inputs" / "run_a_copy"
    archived.mkdir(parents=True)
    for name in ("run.json", "search.ndjson"):
        (archived / name).write_bytes((runs / "run_a" / name).read_bytes())
    backup = runs / "_backup_old" / "run_a_copy"
    backup.mkdir(parents=True)
    for name in ("run.json", "search.ndjson"):
        (backup / name).write_bytes((runs / "run_a" / name).read_bytes())

    doc, _ = _run_export(tmp_path, top_n=10)
    assert doc["counts"]["ndjson_files"] == 1
    assert doc["counts"]["selected"] == 1


def test_require_acoustics_skips_missing_response(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_a",
        [
            _row("missing", "s1", objective=1.0, generator=GEN_OSSE),
            _row("present", "s2", objective=2.0, generator=GEN_OSSE),
        ],
    )
    (runs / "run_a" / "designs" / "missing" / "response.npz").unlink()

    doc, _ = _run_export(tmp_path, top_n=10, require_acoustics=True)
    assert [design["design_hash"] for design in doc["designs"]] == ["present"]
    assert doc["counts"]["skipped_no_acoustics"] >= 1


def test_metrics_json_fallback_when_row_metrics_missing(tmp_path):
    runs = tmp_path / "runs"
    run = _write_run(
        runs,
        "run_a",
        [_row("d1", "s1", objective=1.0, generator=GEN_OSSE, metrics={})],
    )
    (run / "designs" / "d1" / "metrics.json").write_text(
        json.dumps(
            {
                "freqs_hz": [300.0, 1000.0, 3000.0],
                "di_db": [3.0, 8.0, 12.0],
                "scalars": {"di_mean_db": 8.0},
                "di_source": "balloon",
            }
        ),
        encoding="utf-8",
    )

    doc, _ = _run_export(tmp_path, top_n=1)
    design = doc["designs"][0]
    assert design["metrics"]["arrays"]["freqs_hz"] == [300.0, 1000.0, 3000.0]
    assert design["metrics"]["scalars"]["di_mean_db"] == 8.0
    assert design["metrics"]["di_source"] == "balloon"


# --------------------------------------------------------------------------- output shape


def test_csv_json_npz_are_consistent(tmp_path):
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "run_a",
        [_row("d1", "s1", objective=1.5, generator=GEN_OSSE)],
    )
    doc, out = _run_export(tmp_path, top_n=1)
    design = doc["designs"][0]

    header, rows = _read_csv(out / "top_designs.csv")
    assert len(rows) == 1
    assert "param_L_mm" in header
    assert "term_rip" in header
    assert "metric_di_mean_db" in header
    assert rows[0]["typology"] == "OSSE"
    assert rows[0]["score_set"] == "v7"
    assert rows[0]["objective"] == "1.5"
    assert rows[0]["rank"] == "1"

    assert design["params"]["L_mm"] == 250.0
    assert design["terms"]["rip"] == 0.5
    assert design["metrics"]["arrays"]["freqs_hz"] == [300.0, 1000.0, 3000.0]
    assert design["metrics"]["scalars"]["di_mean_db"] == 8.0
    assert design["dimensions"]["bbox_quadrant_mm"] == [100.0, 120.0, 200.0]
    assert design["dimensions"]["mouth_width_mm_est"] == 200.0
    assert design["dimensions"]["mouth_height_mm_est"] == 240.0
    assert design["dimensions"]["depth_mm_est"] == 200.0
    assert design["dimensions"]["area_m2_quadrant"] == 0.05
    assert design["dimensions"]["area_m2_full_est"] == 0.2

    assert design["score_config_sha"] in doc["score_configs"]
    assert doc["score_configs"][design["score_config_sha"]]["target"]["band_lo_hz"] == 300.0
    assert design["run_rel"] in doc["runs"]
    assert doc["runs"][design["run_rel"]]["config_name"] == "cfg"

    acoustics_id = design["acoustics_id"]
    assert acoustics_id
    with np.load(out / "top_designs_acoustics.npz") as archive:
        key = f"{acoustics_id}__spl_h_db"
        assert key in archive.files
        assert archive[key].dtype == np.float32
        assert archive[key].shape == (3, 3)
        z_key = f"{acoustics_id}__z_throat"
        assert archive[z_key].dtype == np.complex128
    assert "spl_h_db" in design["acoustics_arrays"]


def test_no_acoustics_writes_csv_and_json_only(tmp_path):
    runs = tmp_path / "runs"
    _write_run(runs, "run_a", [_row("d1", "s1", objective=1.0, generator=GEN_OSSE)])
    doc, out = _run_export(tmp_path, top_n=1, write_acoustics=False)
    assert (out / "top_designs.csv").is_file()
    assert (out / "top_designs.json").is_file()
    assert not (out / "top_designs_acoustics.npz").exists()
    assert doc["designs"][0]["acoustics_id"] is None
    assert doc["counts"]["acoustics_array_count"] == 0


def test_cli_writes_default_names(tmp_path):
    runs = tmp_path / "runs"
    _write_run(runs, "run_a", [_row("d1", "s1", objective=1.0, generator=GEN_OSSE)])
    out = tmp_path / "cli_out"
    assert (
        top_designs.main(
            [
                "--runs",
                str(runs),
                "--out",
                str(out),
                "--top",
                "1",
                "--quiet",
            ]
        )
        == 0
    )
    assert (out / "top_designs.csv").is_file()
    assert (out / "top_designs.json").is_file()
    assert (out / "top_designs_acoustics.npz").is_file()
