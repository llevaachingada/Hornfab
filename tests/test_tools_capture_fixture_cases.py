"""Offline tests for ``tools/system/capture_fixture_cases.py``.

Hermetic: every test builds a synthetic ``system_runs`` store under ``tmp_path``.  No real store,
no GPU, no solver, no Boundary Lab import.  The tool is loaded by path, matching the
``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from conftest import REPO

TOOL = REPO / "tools" / "system" / "capture_fixture_cases.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("capture_fixture_cases_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


capture = _load_tool()


# --------------------------------------------------------------------------- fixtures


def _case(store: Path, experiment: str, name: str) -> Path:
    case_dir = store / "system" / experiment / name
    case_dir.mkdir(parents=True)
    return case_dir


def _manifest(case_dir: Path, kind: str, extra: dict | None = None) -> Path:
    payload = {"kind": kind}
    if extra:
        payload.update(extra)
    path = case_dir / "manifest.json"
    path.write_text(json.dumps({"created_utc": "2026-01-01T00:00:00Z", "payload": payload}),
                    encoding="utf-8")
    return path


def _dump(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _make_store(root: Path) -> Path:
    store = root / "system_runs"
    # alpha appears in two experiments: exp_a must win the (experiment, case) ordering.
    a = _case(store, "exp_a", "20260101T000000Z-alpha")
    _manifest(a, "alpha")
    _dump(a / "request.json", {"driver": "A"})
    b = _case(store, "exp_b", "20260101T000000Z-alpha")
    _manifest(b, "alpha")
    beta = _case(store, "exp_b", "20260101T000001Z-beta")
    _manifest(beta, "beta")
    gamma = _case(store, "exp_c", "20260101T000002Z-gamma")
    _manifest(gamma, "gamma")
    _case(store, "exp_c", "20260101T000003Z-broken")  # no manifest -> invalid
    # Non-records that discovery must ignore.
    ignored = _case(store, "exp_d", "not-a-timestamp")
    _manifest(ignored, "alpha")
    hidden = _case(store, "_fixtures", "20260101T000004Z-hidden")
    _manifest(hidden, "alpha")
    return store


# --------------------------------------------------------------------------- tests


def test_selection_is_first_n_per_kind_by_experiment_case(tmp_path):
    store = _make_store(tmp_path)
    out = tmp_path / "fixtures"

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    provenance = json.loads((out / "FIXTURE_PROVENANCE.json").read_text(encoding="utf-8"))
    cases = {entry["case_key"]: entry["kind"] for entry in provenance["cases"]}

    assert cases == {
        "exp_a/20260101T000000Z-alpha": "alpha",
        "exp_b/20260101T000001Z-beta": "beta",
        "exp_c/20260101T000002Z-gamma": "gamma",
        "exp_c/20260101T000003Z-broken": "invalid",
    }
    assert provenance["kinds_covered"] == ["alpha", "beta", "gamma", "invalid"]
    # The second alpha case and every non-record stay out.
    assert not (out / "system" / "exp_b" / "20260101T000000Z-alpha").exists()
    assert not (out / "system" / "exp_d").exists()
    assert not (out / "system" / "_fixtures").exists()


def test_copy_conserves_layout_and_bytes(tmp_path):
    store = _make_store(tmp_path)
    out = tmp_path / "fixtures"
    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    source = store / "system" / "exp_a" / "20260101T000000Z-alpha"
    target = out / "system" / "exp_a" / "20260101T000000Z-alpha"
    assert (target / "manifest.json").read_bytes() == (source / "manifest.json").read_bytes()
    assert (target / "request.json").read_bytes() == (source / "request.json").read_bytes()


def test_size_and_extension_filters(tmp_path):
    store = _make_store(tmp_path)
    case = store / "system" / "exp_a" / "20260101T000000Z-alpha"
    _dump(case / "nested" / "small.json", {"ok": True})
    (case / "big.json").write_bytes(b"{" + b" " * (capture.MAX_FILE_BYTES) + b"}")
    (case / "data.npz").write_bytes(b"PK\x03\x04 fake npz")
    (case / "mesh.msh").write_bytes(b"$MeshFormat")
    (case / "notes.txt").write_bytes(b"not json")
    out = tmp_path / "fixtures"

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    target = out / "system" / "exp_a" / "20260101T000000Z-alpha"
    assert (target / "nested" / "small.json").is_file()
    assert not (target / "big.json").exists()
    assert not (target / "data.npz").exists()
    assert not (target / "mesh.msh").exists()
    assert not (target / "notes.txt").exists()

    provenance = json.loads((out / "FIXTURE_PROVENANCE.json").read_text(encoding="utf-8"))
    entry = next(item for item in provenance["cases"] if item["kind"] == "alpha")
    omitted = {item["path"]: item["reason"] for item in entry["omitted"]}
    assert omitted["system/exp_a/20260101T000000Z-alpha/big.json"] == "too_large"
    assert omitted["system/exp_a/20260101T000000Z-alpha/data.npz"] == "array_extension"
    assert omitted["system/exp_a/20260101T000000Z-alpha/mesh.msh"] == "array_extension"
    assert omitted["system/exp_a/20260101T000000Z-alpha/notes.txt"] == "not_json"


def test_include_arrays_copies_small_arrays_only(tmp_path):
    store = _make_store(tmp_path)
    case = store / "system" / "exp_a" / "20260101T000000Z-alpha"
    (case / "small.npz").write_bytes(b"PK\x03\x04 small")
    (case / "huge.npz").write_bytes(b"x" * (capture.MAX_FILE_BYTES + 1))
    out = tmp_path / "fixtures"

    assert capture.main(
        ["--store", str(store), "--out", str(out), "--per-kind", "1", "--include-arrays"]
    ) == 0

    target = out / "system" / "exp_a" / "20260101T000000Z-alpha"
    assert (target / "small.npz").read_bytes() == (case / "small.npz").read_bytes()
    assert not (target / "huge.npz").exists()


def test_provenance_records_source_paths_and_sha256(tmp_path):
    store = _make_store(tmp_path)
    out = tmp_path / "fixtures"
    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "2"]) == 0

    provenance = json.loads((out / "FIXTURE_PROVENANCE.json").read_text(encoding="utf-8"))
    assert provenance["tool"] == "capture_fixture_cases"
    assert provenance["tool_version"] == "1"
    assert provenance["per_kind"] == 2
    assert provenance["diagnostics"] == []

    for entry in provenance["cases"]:
        assert entry["source"] == f"system/{entry['case_key']}"
        assert not Path(entry["source"]).is_absolute()
        for item in entry["files"]:
            copied = out / item["path"]
            data = copied.read_bytes()
            assert copied.stat().st_size == item["size_bytes"]
            assert item["sha256"] == hashlib.sha256(data).hexdigest()
            assert item["path"].startswith("system/")

    all_paths = [item["path"] for entry in provenance["cases"] for item in entry["files"]]
    assert len(all_paths) == len(set(all_paths))
    assert "system/exp_a/20260101T000000Z-alpha/manifest.json" in all_paths


def test_output_is_byte_identical_across_runs(tmp_path):
    store = _make_store(tmp_path)
    out_one = tmp_path / "one"
    out_two = tmp_path / "two"

    assert capture.main(["--store", str(store), "--out", str(out_one), "--per-kind", "2"]) == 0
    assert capture.main(["--store", str(store), "--out", str(out_two), "--per-kind", "2"]) == 0

    assert _tree(out_one) == _tree(out_two)


def test_refuses_to_write_inside_store(tmp_path):
    store = _make_store(tmp_path)
    out = store / "fixtures"
    before = sorted(path.relative_to(store).as_posix() for path in store.rglob("*"))

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 2

    assert not out.exists()
    after = sorted(path.relative_to(store).as_posix() for path in store.rglob("*"))
    assert after == before


def test_reads_but_never_writes_the_store(tmp_path):
    store = _make_store(tmp_path)
    out = tmp_path / "fixtures"
    before = _tree(store)

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    assert _tree(store) == before


def test_odd_store_is_a_diagnostic_not_a_crash(tmp_path):
    store = tmp_path / "system_runs"
    odd = _case(store, "exp_a", "20260101T000000Z-no-kind")
    (odd / "manifest.json").write_text(json.dumps({"payload": {"result": "{}"}}), encoding="utf-8")
    out = tmp_path / "fixtures"

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    provenance = json.loads((out / "FIXTURE_PROVENANCE.json").read_text(encoding="utf-8"))
    assert provenance["cases"] == []
    assert provenance["kinds_covered"] == []
    assert [item["reason"] for item in provenance["diagnostics"]] == ["payload kind missing"]


def test_missing_system_directory_is_a_diagnostic_not_a_crash(tmp_path):
    store = tmp_path / "system_runs"
    store.mkdir()
    out = tmp_path / "fixtures"

    assert capture.main(["--store", str(store), "--out", str(out), "--per-kind", "1"]) == 0

    provenance = json.loads((out / "FIXTURE_PROVENANCE.json").read_text(encoding="utf-8"))
    assert provenance["cases"] == []
    assert provenance["diagnostics"][0]["reason"] == "store has no system/ directory"
