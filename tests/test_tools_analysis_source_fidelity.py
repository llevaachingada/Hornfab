"""Offline tests for tools/analysis/source_fidelity.py (S6, M1).

Synthetic catalog/dataset/run fixtures only: no BEM, GPU, mesh, DatasetStore or GUI import.
The tests pin the S6 contract:

* one card per native ``ok`` row the catalog can resolve, keyed by ``design_hash``;
* ``di_source`` is read from stored metrics and never inferred (unknown stays ``null``);
* missingness reflects the stored ``.npz`` arrays (balloon / cuts / throat impedance);
* physical size comes from stored design parameters (no invented B2 join);
* verify pairing reuses the public fidelity resolver and requires same-run exact physical
  provenance (a shared ``design_hash`` across runs is never paired);
* ambiguous run provenance and absent verify rows stay explicit;
* the emitted JSON/MD carry the frozen source context and a before/after source guard.
"""
from __future__ import annotations

import importlib.util
import json
import sys

import numpy as np
import pytest

from conftest import REPO

_TOOL = REPO / "tools" / "analysis" / "source_fidelity.py"
NATIVE = "native__ath_core_v4"


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sf = _load_tool("source_fidelity_tool", _TOOL)


# ------------------------------------------------------------------ fixtures

def _arrays(*, balloon=True, z=True, cuts=True, di_source="balloon", n_freq=3):
    out = {
        "freqs_hz": np.linspace(500.0, 8000.0, n_freq),
        "h_angles_deg": np.array([-90.0, 0.0, 90.0]),
        "v_angles_deg": np.array([-90.0, 0.0, 90.0]),
        "spl_h_db": np.zeros((n_freq, 3)),
        "spl_v_db": np.zeros((n_freq, 3)),
        "bw_h_deg": np.ones(n_freq) * 50.0,
        "bw_v_deg": np.ones(n_freq) * 50.0,
        "di_db": np.ones(n_freq) * 12.0,
        "ripple_h_db": np.zeros(n_freq),
        "ripple_v_db": np.zeros(n_freq),
        "on_axis_db": np.zeros(n_freq),
    }
    if balloon:
        out["balloon_dirs"] = np.zeros((8, 3))
        out["spl_balloon_db"] = np.zeros((n_freq, 8))
    if z:
        out["z_throat"] = np.ones(n_freq, dtype=complex)
    if not cuts:
        for key in ("spl_h_db", "spl_v_db", "h_angles_deg", "v_angles_deg",
                    "di_db", "ripple_h_db", "ripple_v_db", "on_axis_db"):
            out.pop(key)
    return out


def _meta(design_hash, mesh_hash, solve_hash, *, fidelity="screen", backend="beat_cuda",
          di_source="balloon", params=None, f11=3957.14, with_di_source=True):
    metrics: dict = {
        "f11_hz": f11,
        "di_mean_db": 12.0,
        "ripple_mean_db": 1.0,
        "bw_h_mean_deg": 50.0,
        "bw_v_mean_deg": 50.0,
    }
    if with_di_source:
        metrics["di_source"] = di_source
    return {
        "ok": True,
        "design_hash": design_hash,
        "mesh_hash": mesh_hash,
        "solve_hash": solve_hash,
        "family": "OSSE",
        "params": params if params is not None else {
            "morph_width_mm": 397.0, "morph_height_mm": 410.0, "L_mm": 260.0,
        },
        "mesh": {"n_triangles": 100, "n_dof": 50},
        "solve": {"mode": fidelity, "backend": backend},
        "metrics_scalars": metrics,
        "terms": {"di_estimated": 0.0},
        "objective": 1.5,
        "objective_version": 4,
    }


def _catalog_row(design_hash, mesh_hash, solve_hash, *, shard=0, row=0,
                 fidelity="screen", backend="beat_cuda", config=NATIVE, ok="True",
                 physical=None):
    return {
        "root": "dataset", "shard": f"shard-{shard:04d}.jsonl", "shard_index": shard,
        "row": row, "design_hash": design_hash, "mesh_hash": mesh_hash,
        "solve_hash": solve_hash, "physical_solve_id": physical or f"p-{design_hash}",
        "family": "OSSE", "ok": ok, "failure_kind": "", "objective": 1.5,
        "objective_version": 4, "brief": "native_ath_core_2in_v4",
        "brief_hash": "fb", "config_name": config, "run_id": "", "experiment_id": "",
        "fidelity": fidelity, "backend": backend, "grid_hash": "g", "mesh_spec_id": "m",
        "solve_spec_id": "s", "dependency_hash": "d", "software_hash": "sw",
        "own_commit": "c", "task_identity": "t", "score_identity": "sc",
        "score_parameters_known": "False", "completeness": "complete",
        "missing_score_arrays": "", "missing_loading_arrays": "", "gate_failures": "",
        "npz_readable": "True", "unknowns": "", "index_mismatches": "",
    }


def _write_catalog(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    import csv
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_dataset(root, metas, arrays):
    root.mkdir(parents=True, exist_ok=True)
    shard = root / "shard-0000"
    shard.mkdir(parents=True, exist_ok=True)
    (root / "shard-0000.jsonl").write_text(
        "\n".join(json.dumps(m) for m in metas) + "\n", encoding="utf-8")
    for i, arr in enumerate(arrays):
        np.savez(shard / f"rec-{i:04d}.npz", **arr)


def _write_run(runs_root, run_id, search_rows, verify_rows):
    run = runs_root / run_id
    run.mkdir(parents=True, exist_ok=True)
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in search_rows) + "\n", encoding="utf-8")
    if verify_rows is not None:
        (run / "verify").mkdir(parents=True, exist_ok=True)
        (run / "verify" / "search.ndjson").write_text(
            "\n".join(json.dumps(r) for r in verify_rows) + "\n", encoding="utf-8")


def _run_row(design_hash, mesh_hash, solve_hash, *, mode="screen", n=0):
    return {"mode": mode, "design_hash": design_hash, "mesh_hash": mesh_hash,
            "solve_hash": solve_hash, "n": n, "objective": 1.5, "ok": True}


def _write_scores(path, rows, counts=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tool": "offline_scores", "rows": rows,
                                "counts": counts or {"scored": len(rows)}}),
                    encoding="utf-8")


def _write_brief(path, *, load=0.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "name": "native_ath_core_2in_v4",
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
                    "load": load, "distd": 0.5, "diag": 0.5},
        "target": {"band_lo_hz": 300.0, "band_hi_hz": 8000.0, "f0_hz": 1280.0},
        "objective": {"version": 4, "tolerances": {"cov": 2.0}},
    }), encoding="utf-8")


def _case(tmp_path, rows, *, runs_spec=None, score_rows=None, brief_load=0.0):
    """Build one temp case.

    ``rows`` is a list of dicts: ``{meta, arrays, catalog}``; catalog defaults are derived
    from the meta. ``runs_spec`` is a list of ``(run_id, search_rows, verify_rows)``.
    """
    catalog_rows, metas, arrays = [], [], []
    for i, item in enumerate(rows):
        meta = item["meta"]
        cat = item.get("catalog") or _catalog_row(
            meta["design_hash"], meta["mesh_hash"], meta["solve_hash"],
            shard=0, row=i, fidelity=meta["solve"].get("mode", "screen"),
            backend=meta["solve"].get("backend", "beat_cuda"))
        catalog_rows.append(cat)
        metas.append(meta)
        arrays.append(item["arrays"])

    catalog = tmp_path / "catalog.csv"
    dataset = tmp_path / "dataset"
    runs = tmp_path / "runs"
    brief = tmp_path / "brief.yaml"
    scores = tmp_path / "scores.json"
    out = tmp_path / "out"
    _write_catalog(catalog, catalog_rows)
    _write_dataset(dataset, metas, arrays)
    runs.mkdir(parents=True, exist_ok=True)
    for spec in runs_spec or []:
        _write_run(runs, *spec)
    _write_brief(brief, load=brief_load)
    _write_scores(scores, score_rows or [])
    payload = sf.analyse(scores=scores, catalog=catalog, dataset=dataset, runs=runs,
                         brief=brief, out=out)
    return payload, {"catalog": catalog, "dataset": dataset, "runs": runs,
                     "brief": brief, "scores": scores, "out": out}


def _cards(payload):
    return {c["design_hash"]: c for c in payload["designs"]}


# ------------------------------------------------------------------ selection + counts

def test_cards_cover_native_ok_rows_only(tmp_path):
    rows = [
        {"meta": _meta("aaa", "m-a", "s-a"), "arrays": _arrays()},
        {"meta": _meta("bbb", "m-b", "s-b", fidelity="verify"), "arrays": _arrays()},
        {"meta": _meta("bbb2", "m-b", "s-b2", fidelity="screen"), "arrays": _arrays(),
         "catalog": _catalog_row("bbb", "m-b", "s-b2", row=2, fidelity="screen")},
        {"meta": _meta("ccc", "m-c", "s-c"), "arrays": _arrays(),
         "catalog": _catalog_row("ccc", "m-c", "s-c", row=3, ok="False")},
        {"meta": _meta("ddd", "m-d", "s-d"), "arrays": _arrays(),
         "catalog": _catalog_row("ddd", "m-d", "s-d", row=4, config="other_config")},
    ]
    payload, _ = _case(tmp_path, rows)
    cohort = payload["cohort"]
    assert cohort["rows"] == 3                    # aaa + bbb(screen) + bbb(verify)
    assert cohort["unique_design_hash"] == 2      # bbb has screen+verify physical rows
    assert cohort["screen_vs_verify"] == {"screen": 2, "verify": 1}
    assert {c["design_hash"] for c in payload["designs"]} == {"aaa", "bbb"}
    assert cohort["config"] == NATIVE


# ------------------------------------------------------------------ DI source / missingness

def test_di_source_is_read_and_unknown_stays_null(tmp_path):
    rows = [
        {"meta": _meta("cuts", "m1", "s1", di_source="cuts_estimate"), "arrays": _arrays()},
        {"meta": _meta("unk", "m2", "s2", with_di_source=False), "arrays": _arrays()},
    ]
    payload, _ = _case(tmp_path, rows)
    cards = _cards(payload)
    assert cards["cuts"]["di_source"] == "cuts_estimate"
    assert cards["unk"]["di_source"] is None
    assert "di_source_absent" in cards["unk"]["di_source_evidence"]["reason"]
    assert payload["cohort"]["di_source_counts"] == {"cuts_estimate": 1, "unknown": 1}


def test_missingness_reflects_stored_arrays(tmp_path):
    rows = [
        {"meta": _meta("full", "m1", "s1"), "arrays": _arrays()},
        {"meta": _meta("bare", "m2", "s2"), "arrays": _arrays(balloon=False, z=False,
                                                             cuts=False)},
    ]
    payload, _ = _case(tmp_path, rows)
    cards = _cards(payload)
    assert cards["full"]["missingness"]["balloon"]["present"] is True
    assert cards["full"]["missingness"]["z"]["present"] is True
    assert cards["full"]["missingness"]["cuts"]["present"] is True
    assert cards["bare"]["missingness"]["balloon"]["present"] is False
    assert cards["bare"]["missingness"]["z"]["present"] is False
    assert cards["bare"]["missingness"]["cuts"]["present"] is False
    assert set(cards["bare"]["missingness"]["balloon"]["missing_arrays"]) == {
        "balloon_dirs", "spl_balloon_db"}
    assert payload["cohort"]["with_balloon"] == 1
    assert payload["cohort"]["with_z"] == 1


def test_physical_size_from_stored_design_params(tmp_path):
    meta = _meta("size", "m1", "s1", params={
        "morph_width_mm": 401.5, "morph_height_mm": 388.0, "L_mm": 272.0})
    payload, _ = _case(tmp_path, [{"meta": meta, "arrays": _arrays()}])
    size = _cards(payload)["size"]["physical_size"]
    assert size["mouth_w_mm"] == pytest.approx(401.5)
    assert size["mouth_h_mm"] == pytest.approx(388.0)
    assert size["depth_mm"] == pytest.approx(272.0)
    assert size["source"] == "stored_design_params"
    assert size["b2_geometry_descriptors"]["joinable"] is False


# ------------------------------------------------------------------ pairing

def _paired_case(tmp_path, *, ver_key=None, screen_key=None, runs_spec=None):
    screen_key = screen_key or ("pair", "mesh", "solve-screen")
    ver_key = ver_key or ("pair", "mesh", "solve-verify")
    rows = [
        {"meta": _meta(screen_key[0], screen_key[1], screen_key[2]),
         "arrays": _arrays(),
         "catalog": _catalog_row(screen_key[0], screen_key[1], screen_key[2], row=0,
                                 fidelity="screen", physical="p-screen")},
        {"meta": _meta(ver_key[0], ver_key[1], ver_key[2], fidelity="verify"),
         "arrays": _arrays()},
    ]
    # catalog rows: screen at row 0, verify at row 1
    rows[1]["catalog"] = _catalog_row(ver_key[0], ver_key[1], ver_key[2], row=1,
                                      fidelity="verify", physical="p-verify")
    runs = runs_spec or [("run-1", [_run_row(*screen_key, mode="screen", n=5)],
                          [_run_row(*ver_key, mode="verify", n=0)])]
    return _case(tmp_path, rows, runs_spec=runs)


def test_verify_pairing_reuses_fidelity_resolver(tmp_path):
    payload, _ = _paired_case(tmp_path)
    cards = _cards(payload)
    screen = cards["pair"]
    # the dict key is design_hash, so the verify row overwrites the screen in _cards; use list
    pair_cards = [c for c in payload["designs"] if c["design_hash"] == "pair"]
    assert len(pair_cards) == 2
    for card in pair_cards:
        pairing = card["verify_pairing"]
        assert pairing["status"] == "paired"
        assert pairing["method"] == "reused_tools.analysis.fidelity.analyse_run"
        assert pairing["run_id"] == "run-1"
        assert pairing["resolver_pair"]["j_screen"] == pytest.approx(1.5)
    by_fid = {c["fidelity"]: c for c in pair_cards}
    assert by_fid["screen"]["verify_pairing"]["paired_fidelity"] == "verify"
    assert by_fid["verify"]["verify_pairing"]["paired_fidelity"] == "screen"
    assert by_fid["screen"]["verify_pairing"]["paired_physical_solve_id"] == "p-verify"
    assert by_fid["verify"]["verify_pairing"]["paired_physical_solve_id"] == "p-screen"
    assert payload["cohort"]["pairing_status_counts"] == {"paired": 2}
    assert payload["cohort"]["verify_runs_found"] == 1


def test_cross_run_design_hash_is_never_paired(tmp_path):
    row_s = _run_row("pair", "mesh", "solve-screen", mode="screen", n=1)
    row_v = _run_row("pair", "mesh", "solve-verify", mode="verify", n=0)
    runs = [("run-screen", [row_s], None), ("run-verify", [], [row_v])]
    payload, _ = _paired_case(tmp_path, runs_spec=runs)
    for card in [c for c in payload["designs"] if c["design_hash"] == "pair"]:
        pairing = card["verify_pairing"]
        assert pairing["status"] == "pairing_unavailable"
        assert "screen_counterpart_not_in_same_run" in pairing["reasons"]
        assert pairing["paired_design_hash"] is None
    assert payload["cohort"]["pairing_status_counts"] == {"pairing_unavailable": 2}


def test_ambiguous_run_provenance_is_pairing_unavailable(tmp_path):
    row_s = _run_row("pair", "mesh", "solve-screen", mode="screen", n=1)
    row_v = _run_row("pair", "mesh", "solve-verify", mode="verify", n=0)
    runs = [("run-1", [row_s], [row_v]), ("run-2", [row_s, row_v], None)]
    payload, _ = _paired_case(tmp_path, runs_spec=runs)
    for card in [c for c in payload["designs"] if c["design_hash"] == "pair"]:
        pairing = card["verify_pairing"]
        assert pairing["status"] == "pairing_unavailable"
        assert "run_provenance_ambiguous" in pairing["reasons"]
    assert payload["cohort"]["run_provenance_counts"]["ambiguous"] == 2


def test_no_verify_row_is_explicit(tmp_path):
    payload, _ = _case(
        tmp_path,
        [{"meta": _meta("solo", "m1", "s1"), "arrays": _arrays()}],
        runs_spec=[("run-1", [_run_row("solo", "m1", "s1")], None)],
    )
    card = _cards(payload)["solo"]
    assert card["verify_pairing"]["status"] == "no_verify_row"
    assert card["verify_pairing"]["reasons"] == [
        "no_verify_row_for_design_in_native_cohort"]
    assert payload["cohort"]["pairing_status_counts"] == {"no_verify_row": 1}


def test_pairing_falls_back_when_fidelity_resolver_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(sf, "_load_fidelity_resolver",
                        lambda: (None, "ImportError: simulated"))
    payload, _ = _paired_case(tmp_path)
    for card in [c for c in payload["designs"] if c["design_hash"] == "pair"]:
        pairing = card["verify_pairing"]
        assert pairing["status"] == "paired"
        assert pairing["method"] == "run_provenance_exact_physical_identity"
        assert any("fidelity_resolver_unavailable" in w for w in pairing["warnings"])
    assert payload["cohort"]["fidelity_resolver"] == "unavailable: ImportError: simulated"


# ------------------------------------------------------------------ offline score join / schema

def test_offline_score_join_by_design_hash(tmp_path):
    score_rows = [{"design_hash": "aaa", "status": "exact_complete", "j": 1.5,
                   "shard": 0, "row": 0}]
    payload, _ = _case(
        tmp_path,
        [{"meta": _meta("aaa", "m1", "s1"), "arrays": _arrays()},
         {"meta": _meta("bbb", "m2", "s2"), "arrays": _arrays()}],
        score_rows=score_rows,
    )
    cards = _cards(payload)
    assert cards["aaa"]["offline_score"]["status"] == "exact_complete"
    assert cards["bbb"]["offline_score"] is None
    assert payload["cohort"]["offline_scores_rows_matched"] == 1


def test_artifact_schema_markdown_and_source_guard(tmp_path):
    payload, paths = _paired_case(tmp_path)
    out = paths["out"]
    assert (out / "source_fidelity.json").is_file()
    assert (out / "source_fidelity.md").is_file()
    disk = json.loads((out / "source_fidelity.json").read_text(encoding="utf-8"))
    assert disk["tool"] == "source_fidelity"
    assert disk["schema_version"] == 1
    assert disk["protocol"] == "bo-study-v1.1"
    assert disk["read_only"] is True
    ctx = disk["source_assumption_context"]
    assert ctx["f11_hz"] == 3957.0
    assert ctx["loading_weight"] == 0.0
    assert ctx["loading_weight_consistent"] is True
    assert ctx["band_hz"] == [300.0, 8000.0]
    assert ctx["f0_hz"] == 1280.0
    assert disk["task_identity"]["weights"]["load"] == 0.0
    assert disk["source_guard"]["unchanged"] is True
    assert disk["source_guard"]["files_checked"] == 8
    # JSON is machine-readable with sorted keys and no internal _key leaking
    assert all("_key" not in card for card in disk["designs"])
    assert "# Source fidelity" in (out / "source_fidelity.md").read_text(encoding="utf-8")


def test_snapshot_detects_changed_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("one", encoding="utf-8")
    before = sf._snapshot_paths([p])
    p.write_text("two", encoding="utf-8")
    after = sf._snapshot_paths([p])
    guard = sf._compare_snapshot(before, after)
    assert guard["unchanged"] is False
    assert any("content changed" in problem for problem in guard["problems"])


def test_source_guard_flags_violation_via_main(tmp_path, monkeypatch):
    payload, paths = _paired_case(tmp_path)
    assert payload["source_guard"]["unchanged"] is True
    # A read-only run writes only the two artifacts inside --out.
    written = sorted(p.name for p in paths["out"].iterdir())
    assert written == ["source_fidelity.json", "source_fidelity.md"]
    assert sorted(p.name for p in paths["dataset"].iterdir()) == [
        "shard-0000", "shard-0000.jsonl"]
