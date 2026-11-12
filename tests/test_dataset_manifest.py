"""Tests for hornlab_search.dataset.manifest (MANIFEST.json). Offline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hornlab_search.dataset.manifest import (DEFAULT_LAB, MANIFEST_NAME, RELABEL_NOTE,
                                             build_manifest, main, write_manifest)
from hornlab_search.dataset.record import build_record
from test_dataset_factory import (GRID, LIB_SHAS, LIB_SHAS_B, TARGET, make_eval, solve_spec)


def _record(i: int, *, family: str = "OSSE", mode: str = "screen", lib=LIB_SHAS,
            objective_version: int = 1, typology: str | None = None, created: str = "2026-10-13T00:00:00Z"):
    meta, _ = build_record(make_eval(i, family), TARGET, lib,
                           solve_spec=solve_spec(mode=mode), grid=GRID, area_m2=0.125,
                           objective_version=objective_version, typology=typology,
                           created_utc=created)
    return meta


def _write_shard(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows),
                    encoding="utf-8")


def _dataset(tmp_path: Path) -> Path:
    root = tmp_path / "dataset"
    root.mkdir()
    _write_shard(root / "shard-0000.jsonl", [
        _record(1, objective_version=7, typology="core:os"),
        _record(2, family="R-OSSE", objective_version=7, typology="core:os"),
    ])
    _write_shard(root / "shard-0001.jsonl", [
        _record(3, mode="verify", lib=LIB_SHAS_B, created="2026-10-14T00:00:00Z"),
    ])
    return root


def test_manifest_census_groups_and_provenance(tmp_path):
    root = _dataset(tmp_path)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("shard-*.jsonl")}
    doc = build_manifest(root, lab="hunter-4060")

    assert doc["schema_version"] == 1 and doc["manifest_version"] == 1
    assert doc["lab"] == DEFAULT_LAB and doc["dataset_root"] == "dataset"
    assert doc["total_rows"] == 3 and doc["ok_rows"] == 3 and doc["failed_rows"] == 0
    assert doc["malformed_lines"] == 0
    assert doc["rows_by_objective_version"] == {"1": 1, "7": 2}
    assert doc["rows_by_family"] == {"OSSE": 2, "R-OSSE": 1}
    assert doc["rows_by_backend"] == {"beat_cuda": 3}
    assert doc["rows_by_mode"] == {"screen": 2, "verify": 1}
    assert doc["rows_by_typology"] == {"OSSE": 1, "core:os": 2}
    assert doc["rows_by_objective_version_family_backend_mode"]["7|OSSE|beat_cuda|screen"] == 1
    assert doc["rows_by_objective_version_family_backend_mode_typology"][
        "1|OSSE|beat_cuda|verify|OSSE"] == 1
    assert len(doc["distinct_lib_sha"]) == 2
    assert doc["created_utc_min"] == "2026-10-13T00:00:00Z"
    assert doc["created_utc_max"] == "2026-10-14T00:00:00Z"

    shards = {s["name"]: s for s in doc["shards"]}
    assert shards["shard-0000.jsonl"]["rows"] == 2 and shards["shard-0001.jsonl"]["rows"] == 1
    for name, sha in before.items():
        assert shards[name]["sha256"] == sha

    assert set(doc["objective_versions"]) == {str(i) for i in range(1, 8)}
    assert doc["relabel_note"] == RELABEL_NOTE
    # read-only over the shards
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.glob("shard-*.jsonl")} == before


def test_manifest_output_is_deterministic_sorted_and_self_excluding(tmp_path):
    root = _dataset(tmp_path)
    path, doc = write_manifest(root, lab="collin")
    text1 = path.read_text(encoding="utf-8")
    assert path == root / MANIFEST_NAME
    assert json.loads(text1) == doc
    path2, _ = write_manifest(root, lab="collin")
    assert path2.read_text(encoding="utf-8") == text1
    # the manifest itself is not a shard: a second census is byte-identical
    assert build_manifest(root, lab="collin") == doc
    assert doc["total_rows"] == 3


def test_manifest_cli_writes_the_requested_lab_and_path(tmp_path, capsys):
    root = _dataset(tmp_path)
    out = tmp_path / "reports" / "MANIFEST.json"
    assert main(["--dataset-root", str(root), "--lab", "collin", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["lab"] == "collin" and doc["total_rows"] == 3
    assert "manifest:" in capsys.readouterr().out
