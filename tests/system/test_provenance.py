"""Stage-0 tests for the system provenance/manifest layer (SYS-12 read-only discipline)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import provenance as P  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402


def _payload() -> dict:
    return {
        "experiment_id": "pilot",
        "spec": {"schema_version": 1, "mode": "fixed_horn", "n": [1.0, 2.0]},
        "ids": {"study": C.system_study_id({"pool": "x", "seed": 7})},
    }


def test_new_case_dir_is_unique_and_separate(tmp_path: Path) -> None:
    a = P.new_case_dir("exp", store_root=tmp_path)
    b = P.new_case_dir("exp", store_root=tmp_path)
    assert a != b and a.is_dir() and b.is_dir()
    assert a.exists() and b.exists()
    assert "system" in str(a) and "exp" in str(a)


def test_manifest_round_trip_and_integrity(tmp_path: Path) -> None:
    case_dir = P.new_case_dir("pilot", store_root=tmp_path)
    path = P.write_manifest(case_dir, _payload())
    assert path == case_dir / "manifest.json"
    loaded = P.load_manifest(path)
    assert loaded["payload"]["experiment_id"] == "pilot"
    assert loaded["payload"]["ids"]["study"] == _payload()["ids"]["study"]

    # corruption is detected by the recorded checksum, not silently tolerated
    text = json.loads(path.read_text(encoding="utf-8"))
    text["payload"]["experiment_id"] = "tampered"
    path.write_text(json.dumps(text), encoding="utf-8")
    with pytest.raises(C.SchemaError, match="integrity"):
        P.load_manifest(path)


def test_manifest_immutability_rewrites_are_refused(tmp_path: Path) -> None:
    case_dir = P.new_case_dir("pilot", store_root=tmp_path)
    P.write_manifest(case_dir, _payload())
    with pytest.raises(SystemExit, match="immutability"):
        P.write_manifest(case_dir, {"again": 1})


def test_historical_runs_tree_is_refused_for_writes(tmp_path: Path) -> None:
    fake_runs = tmp_path / "hornlab" / "runs" / "20261117T000000Z-screen-abc123"
    fake_runs.mkdir(parents=True)
    with pytest.raises(C.SchemaError, match="historical runs tree"):
        P.assert_not_in_historical_runs(fake_runs / "x.bin", tmp_path / "store")
    store = tmp_path / "store"
    store.mkdir()
    P.assert_not_in_historical_runs(store / "sub" / "x.bin", store)  # allowed
    elsewhere = tmp_path / "other_runs" / "deeper"
    elsewhere.mkdir(parents=True)
    # only the exact marker directory name binds; unrelated *_runs trees are not protected
    P.assert_not_in_historical_runs(elsewhere / "x.bin", tmp_path / "store")


def test_file_sha256_matches_known_vector(tmp_path: Path) -> None:
    f = tmp_path / "blob.bin"
    f.write_bytes(b"abc")
    # standard sha256("abc")
    assert P.file_sha256(f) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
