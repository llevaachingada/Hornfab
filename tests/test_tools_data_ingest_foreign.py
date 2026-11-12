"""Tests for tools/data/ingest_foreign.py. Offline: validation, tagging, CP-7b parity gate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

import hornlab_search.dataset.record as record_mod
from hornlab_search.dataset.record import build_record, validate_record
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "data"))

import ingest_foreign  # noqa: E402


def _meta_and_arrays(i: int):
    return build_record(make_eval(i), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                        area_m2=0.125, created_utc="2026-10-13T00:00:00Z")


def _write_dataset(root: Path, records: list[tuple[dict, dict]], *, with_arrays: bool = True):
    """One shard, one npz per record (the real store layout: rec-<row>.npz in record order)."""
    root.mkdir(parents=True, exist_ok=True)
    lines = []
    for row_no, (meta, arrays) in enumerate(records):
        lines.append(json.dumps(meta, separators=(",", ":")) + "\n")
        if with_arrays:
            (root / "shard-0000").mkdir(exist_ok=True)
            np.savez(root / "shard-0000" / f"rec-{row_no:04d}.npz", **arrays)
    (root / "shard-0000.jsonl").write_text("".join(lines), encoding="utf-8")
    return root


def _bump_on_axis(arrays: dict, delta_db: float) -> dict:
    bumped = dict(arrays)
    bumped["on_axis_db"] = arrays["on_axis_db"] + delta_db
    return bumped


@pytest.fixture()
def trees(tmp_path):
    """Local dataset with designs 0-3; a foreign lab tree sharing designs 0-2 plus one foreign-only
    design. Both follow the real store layout (shard jsonl + rec-<row>.npz per record)."""
    local = tmp_path / "dataset"
    shared_meta = [_meta_and_arrays(i) for i in (0, 1, 2)]
    extra_meta = _meta_and_arrays(3)
    _write_dataset(local, shared_meta + [extra_meta])
    foreign = _write_dataset(tmp_path / "dataset_ext" / "collin" / "dataset",
                             shared_meta + [extra_meta])
    return {"local": local, "ext": tmp_path / "dataset_ext" / "collin",
            "foreign": foreign, "shared": shared_meta}


def _snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_dry_run_validates_and_reports_parity_without_writing(tmp_path):
    local = tmp_path / "dataset"
    foreign = tmp_path / "dataset_ext" / "collin" / "dataset"
    records = [_meta_and_arrays(i) for i in (0, 1, 2)]
    _write_dataset(local, records)
    _write_dataset(foreign, records)
    before = _snapshot(local)

    doc = ingest_foreign.report(foreign, local, apply=False,
                                backup_root=foreign / "_backup_ingest_lab", lab="collin")

    assert doc["rows_validated"] == 3 and doc["invalid_rows"] == 0
    assert doc["rows_to_tag"] == 3 and doc["applied_tagging"] is False
    parity = doc["parity"]
    assert parity["shared_with_spl"] == 3
    assert parity["shared_within_threshold_db"] == 3
    assert parity["comparable"] is True
    assert parity["group"] == "comparable-with-local"
    for shared in parity["shared_designs"]:
        assert shared["spl"]["max_abs_db"] == 0.0
    # the local dataset is read-only, always
    assert _snapshot(local) == before


def test_parity_gate_needs_three_agreeing_shared_designs(tmp_path):
    local = tmp_path / "dataset"
    foreign = tmp_path / "dataset_ext" / "collin" / "dataset"
    records = [_meta_and_arrays(i) for i in (0, 1, 2)]
    _write_dataset(local, records)
    disagreeing = (_meta_and_arrays(2)[0], _bump_on_axis(records[2][1], 0.5))
    _write_dataset(foreign, [records[0], records[1], disagreeing])

    doc = ingest_foreign.report(foreign, local, apply=False,
                                backup_root=foreign / "_backup_ingest_lab", lab="collin")
    parity = doc["parity"]
    assert parity["shared_with_spl"] == 3
    assert parity["shared_within_threshold_db"] == 2   # 0.5 dB > the 0.2 dB rule
    assert parity["comparable"] is False
    assert parity["group"] == "separate-group"
    assert parity["min_shared_designs"] == 3


def test_common_designs_without_arrays_are_counted_but_never_prove_parity(tmp_path):
    local = tmp_path / "dataset"
    foreign = tmp_path / "dataset_ext" / "collin" / "dataset"
    records = [_meta_and_arrays(i) for i in (0, 1, 2)]
    _write_dataset(local, records)
    _write_dataset(foreign, records, with_arrays=False)
    doc = ingest_foreign.report(foreign, local, apply=False,
                                backup_root=foreign / "_backup_ingest_lab", lab="collin")
    parity = doc["parity"]
    assert len(parity["shared_designs"]) == 3
    assert parity["shared_without_spl_arrays"] == 3
    assert parity["shared_with_spl"] == 0
    assert parity["comparable"] is False


def test_tagging_pass_and_failures_are_reported_and_never_tagged(tmp_path):
    foreign = tmp_path / "dataset_ext" / "collin" / "dataset"
    meta, arrays = _meta_and_arrays(1)
    broken = dict(meta, lib_shas={k: v for k, v in meta["lib_shas"].items() if k != "hornlab_mesher"})
    meta_already = dict(meta, design_hash=meta["design_hash"] + "x2", lab="someone_else")
    rows = [(meta, arrays), (meta_already, _bump_on_axis(arrays, 0.0))]
    lines = [json.dumps(meta), "not json at all {", json.dumps(broken), json.dumps(meta_already)]
    (foreign).mkdir(parents=True)
    (foreign / "shard-0000.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (foreign / "shard-0000").mkdir()
    np.savez(foreign / "shard-0000" / "rec-0000.npz", **arrays)
    np.savez(foreign / "shard-0000" / "rec-0001.npz", **_bump_on_axis(arrays, 0.0))
    local = _write_dataset(tmp_path / "dataset", rows)

    before = (foreign / "shard-0000.jsonl").read_text(encoding="utf-8")
    doc = ingest_foreign.report(foreign, local, apply=False,
                                backup_root=foreign / "_backup_ingest_lab", lab="collin")
    assert doc["rows_validated"] == 2
    assert doc["invalid_rows"] == 1 and any("line 3" in e for e in doc["invalid_examples"])
    assert doc["malformed_lines"] == 1
    assert (foreign / "shard-0000.jsonl").read_text(encoding="utf-8") == before  # dry run

    doc2 = ingest_foreign.report(foreign, local, apply=True,
                                 backup_root=tmp_path / "backup", lab="collin")
    assert doc2["applied_tagging"] is True
    out = [line for line in (foreign / "shard-0000.jsonl").read_text(
        encoding="utf-8").splitlines()]
    assert json.loads(out[0])["lab"] == "collin"
    assert out[1] == "not json at all {"            # malformed line passes through untouched
    assert json.loads(out[2]) == broken             # invalid row passes through untagged
    assert json.loads(out[3])["lab"] == "someone_else"   # existing lab value is never overwritten
    for text in (out[0], out[3]):
        validate_record(json.loads(text))
    assert (tmp_path / "backup" / "shard-0000.jsonl").read_text(encoding="utf-8") == before


def test_local_dataset_never_merges_foreign_rows_and_path_guard_holds(tmp_path):
    records = [_meta_and_arrays(i) for i in (0, 1, 2)]
    local = _write_dataset(tmp_path / "dataset", records)
    before = _snapshot(local)
    with pytest.raises(SystemExit):
        ingest_foreign.report(tmp_path / "dataset" / "collin", local, apply=False,
                              backup_root=tmp_path / "b", lab="collin")
    assert _snapshot(local) == before      # dataset/ untouched, foreign data never merged


def test_climate_of_solve_spec_key_is_part_of_parity(tmp_path):
    """Same design+mesh but a different solve spec (backend) does NOT count as a shared design."""
    meta, arrays = _meta_and_arrays(1)
    foreign_backend = dict(meta,
                           solve=dict(meta["solve"], backend="bempp_cpu"))
    local = _write_dataset(tmp_path / "dataset", [(meta, arrays)])
    foreign = _write_dataset(tmp_path / "dataset_ext" / "collin" / "dataset",
                             [(foreign_backend, arrays)])
    doc = ingest_foreign.report(foreign, local, apply=False,
                                backup_root=tmp_path / "b", lab="collin")
    assert doc["parity"]["shared_designs"] == []
    assert doc["parity"]["comparable"] is False
