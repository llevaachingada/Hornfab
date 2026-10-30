"""Offline tests for ``tools/data/dedupe_runs.py`` (Phase 1 run-store dedupe).

Hermetic: a synthetic run/cache tree under ``tmp_path`` only. No GPU, no solver, no real run
data, no subprocess. The tool is loaded by path (it is a script, not a package module), matching
the ``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from conftest import REPO

TOOL = REPO / "tools" / "data" / "dedupe_runs.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("dedupe_runs_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dedupe = _load_tool()


# ------------------------------------------------------------------ synthetic tree

SHARED = "aaaa00000000"
MISMATCH = "bbbb00000000"
SINGLE = "cccc00000000"
MOUNT = "dddd00000000"

SHARED_MESH_KEY = f"{SHARED}-111111111111"
SHARED_SOLVE_KEY = f"{SHARED_MESH_KEY}-222222222222"
SINGLE_MESH_KEY = f"{SINGLE}-333333333333"
SINGLE_SOLVE_KEY = f"{SINGLE_MESH_KEY}-444444444444"
MOUNT_SOLVE_KEY = f"{MOUNT}-555555555555-666666666666"
MOUNT_CACHE_KEY = f"{MOUNT_SOLVE_KEY}-mnt-abcdef012345"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _design(run: Path, design_hash: str, *, mesh_key: str | None,
            solve_key: str | None) -> Path:
    d = run / "designs" / design_hash
    d.mkdir(parents=True, exist_ok=True)
    _write_json(d / "design.json", {"design_hash": design_hash})
    if mesh_key is not None:
        _write_json(d / "mesh_meta.json", {"key": mesh_key})
    if solve_key is not None:
        _write_json(d / "status.json", {"ok": True, "key": solve_key})
    return d


def _make_tree(tmp_path: Path) -> dict:
    runs = tmp_path / "runs"
    cache_mesh = tmp_path / "cache" / "mesh"
    cache_solve = tmp_path / "cache" / "solve"

    # Canonical cache entries (never touched by the tool).
    mesh_bytes = b"synthetic-mesh-bytes-" * 8
    resp_bytes = b"synthetic-response-bytes-" * 8
    _write(cache_mesh / SHARED_MESH_KEY / "mesh.msh", mesh_bytes)
    _write_json(cache_mesh / SHARED_MESH_KEY / "mesh_meta.json", {"key": SHARED_MESH_KEY})
    _write(cache_solve / SHARED_SOLVE_KEY / "response.npz", resp_bytes)
    _write_json(cache_solve / SHARED_SOLVE_KEY / "status.json", {"ok": True})

    # One run file whose bytes differ from its candidate, same size on purpose: sha256, not
    # size, decides.
    bad_run = b"run:0123456789abcdef"
    bad_cache = b"cch:0123456789abcdef"
    assert len(bad_run) == len(bad_cache)
    bad_key = f"{MISMATCH}-777777777777"
    _write(cache_mesh / bad_key / "mesh.msh", bad_cache)

    # Single-run design: exactly one run file + its cache file -> st_nlink == 2 after linking.
    _write(cache_mesh / SINGLE_MESH_KEY / "mesh.msh", mesh_bytes)
    _write(cache_solve / SINGLE_SOLVE_KEY / "response.npz", resp_bytes)

    # Mounting case: the run key omits the "-mnt-" suffix the cache directory carries.
    _write(cache_solve / MOUNT_CACHE_KEY / "response.npz", resp_bytes)

    run_a = runs / "runA"
    run_b = runs / "runB"

    for run in (run_a, run_b):
        d = _design(run, SHARED, mesh_key=SHARED_MESH_KEY, solve_key=SHARED_SOLVE_KEY)
        _write(d / "mesh.msh", mesh_bytes)
        _write(d / "response.npz", resp_bytes)

    bad = _design(run_a, MISMATCH, mesh_key=bad_key, solve_key=None)
    _write(bad / "mesh.msh", bad_run)

    single = _design(run_a, SINGLE, mesh_key=SINGLE_MESH_KEY, solve_key=SINGLE_SOLVE_KEY)
    _write(single / "mesh.msh", mesh_bytes)
    _write(single / "response.npz", resp_bytes)

    mount = _design(run_a, MOUNT, mesh_key=None, solve_key=MOUNT_SOLVE_KEY)
    _write(mount / "response.npz", resp_bytes)

    return {
        "runs": runs,
        "cache_mesh": cache_mesh,
        "cache_solve": cache_solve,
        "mesh_bytes": mesh_bytes,
        "resp_bytes": resp_bytes,
        "run_a": run_a,
        "run_b": run_b,
        "shared_a_mesh": run_a / "designs" / SHARED / "mesh.msh",
        "shared_a_resp": run_a / "designs" / SHARED / "response.npz",
        "shared_b_mesh": run_b / "designs" / SHARED / "mesh.msh",
        "shared_b_resp": run_b / "designs" / SHARED / "response.npz",
        "bad_mesh": bad / "mesh.msh",
        "bad_cache_mesh": cache_mesh / bad_key / "mesh.msh",
        "single_mesh": single / "mesh.msh",
        "single_resp": single / "response.npz",
        "single_cache_mesh": cache_mesh / SINGLE_MESH_KEY / "mesh.msh",
        "single_cache_resp": cache_solve / SINGLE_SOLVE_KEY / "response.npz",
        "mount_resp": mount / "response.npz",
        "mount_cache_resp": cache_solve / MOUNT_CACHE_KEY / "response.npz",
        "cache_shared_mesh": cache_mesh / SHARED_MESH_KEY / "mesh.msh",
        "cache_shared_resp": cache_solve / SHARED_SOLVE_KEY / "response.npz",
    }


def _argv(t: dict, manifest: Path, *extra: str) -> list[str]:
    return [
        "--runs", str(t["runs"]),
        "--cache-mesh", str(t["cache_mesh"]),
        "--cache-solve", str(t["cache_solve"]),
        "--manifest", str(manifest),
        *extra,
    ]


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 1. dry run is read-only


def test_dry_run_changes_nothing_and_reports_would_link(tmp_path, capsys):
    t = _make_tree(tmp_path)
    manifest = tmp_path / "manifests" / "dry.json"

    watched = [t["shared_a_mesh"], t["shared_b_resp"], t["single_mesh"], t["mount_resp"]]
    before = {
        str(p): (p.read_bytes(), p.stat().st_ino, p.stat().st_nlink) for p in watched
    }

    assert dedupe.main(_argv(t, manifest)) == 0

    for p in watched:
        data, ino, nlink = before[str(p)]
        assert p.read_bytes() == data
        assert p.stat().st_ino == ino
        assert p.stat().st_nlink == 1

    doc = _load_manifest(manifest)
    assert doc["mode"] == "dry-run"
    actions = [e["action"] for e in doc["entries"]]
    assert actions.count("would-link") == 7
    assert "linked" not in actions
    assert doc["counts"]["linked"] == 0
    assert doc["counts"]["would_link"] == 7
    assert doc["counts"]["unmatched"] == 1
    assert doc["bytes_saved"] > 0

    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "would-link" in out


# ------------------------------------------------------------------ 2. --apply links, mismatch refused


def test_apply_links_identical_files_and_leaves_the_mismatch_alone(tmp_path):
    t = _make_tree(tmp_path)
    manifest = tmp_path / "manifests" / "applied.json"
    bad_before = t["bad_mesh"].read_bytes()

    assert dedupe.main(_argv(t, manifest, "--apply")) == 0

    assert os.path.samefile(t["shared_a_mesh"], t["cache_shared_mesh"])
    assert os.path.samefile(t["shared_b_mesh"], t["cache_shared_mesh"])
    assert os.path.samefile(t["shared_a_resp"], t["cache_shared_resp"])
    assert os.path.samefile(t["shared_b_resp"], t["cache_shared_resp"])
    assert os.path.samefile(t["single_mesh"], t["single_cache_mesh"])
    assert os.path.samefile(t["single_resp"], t["single_cache_resp"])
    assert os.path.samefile(t["mount_resp"], t["mount_cache_resp"])

    # Same-sized but different bytes: unmatched, untouched.
    assert t["bad_mesh"].read_bytes() == bad_before
    assert not os.path.samefile(t["bad_mesh"], t["bad_cache_mesh"])
    assert t["bad_mesh"].stat().st_nlink == 1

    doc = _load_manifest(manifest)
    assert doc["mode"] == "apply"
    assert doc["counts"]["linked"] == 7
    assert doc["counts"]["unmatched"] == 1
    assert doc["unmatched_reasons"] == {"sha mismatch": 1}
    bad_entry = next(e for e in doc["entries"] if e["run_file"] == str(t["bad_mesh"]))
    assert bad_entry["action"] == "unmatched"
    assert bad_entry["reason"] == "sha mismatch"


# ------------------------------------------------------------------ 3. idempotent re-run


def test_second_apply_links_nothing_and_does_not_add_links(tmp_path):
    t = _make_tree(tmp_path)
    first = tmp_path / "manifests" / "first.json"
    second = tmp_path / "manifests" / "second.json"

    assert dedupe.main(_argv(t, first, "--apply")) == 0
    # One run file + its cache entry -> exactly two links.
    assert t["single_mesh"].stat().st_nlink == 2
    shared_nlink = t["shared_a_mesh"].stat().st_nlink
    assert shared_nlink == 3          # two runs + the cache entry

    assert dedupe.main(_argv(t, second, "--apply")) == 0

    doc = _load_manifest(second)
    assert doc["counts"]["linked"] == 0
    assert doc["counts"]["already"] == 7
    assert t["single_mesh"].stat().st_nlink == 2
    assert t["shared_a_mesh"].stat().st_nlink == shared_nlink

    assert doc["counts"]["linked"] == 0
    assert doc["counts"]["copy_fallback"] == 0
    assert doc["counts"]["errors"] == 0
    assert doc["counts"]["unmatched"] == 1
    assert "linked" not in [e["action"] for e in doc["entries"]]


# ------------------------------------------------------------------ 4. mounting suffix


def test_mounting_suffix_key_is_found_by_glob(tmp_path):
    t = _make_tree(tmp_path)
    manifest = tmp_path / "manifests" / "mount.json"

    assert dedupe.main(_argv(t, manifest, "--apply")) == 0

    assert os.path.samefile(t["mount_resp"], t["mount_cache_resp"])
    doc = _load_manifest(manifest)
    entry = next(e for e in doc["entries"] if e["run_file"] == str(t["mount_resp"]))
    assert entry["action"] == "linked"
    assert entry["cache_file"] == str(t["mount_cache_resp"])
    assert "-mnt-abcdef012345" in entry["cache_file"]


# ------------------------------------------------------------------ 5. manifest contents


def test_manifest_is_valid_json_with_absolute_linked_paths(tmp_path):
    t = _make_tree(tmp_path)
    manifest = tmp_path / "manifests" / "valid.json"

    assert dedupe.main(_argv(t, manifest, "--apply")) == 0

    doc = _load_manifest(manifest)
    assert doc["generated_utc"]
    assert doc["counts"]["design_dirs_scanned"] == 5
    assert doc["counts"]["mesh_files_examined"] == 4
    assert doc["counts"]["response_files_examined"] == 4

    linked = [e for e in doc["entries"] if e["action"] == "linked"]
    assert len(linked) == 7
    for entry in linked:
        run_file = Path(entry["run_file"])
        cache_file = Path(entry["cache_file"])
        assert run_file.is_file() and cache_file.is_file()
        assert os.path.samefile(run_file, cache_file)

    by_run = {Path(e["run_file"]): e for e in doc["entries"]}
    assert by_run[t["shared_a_mesh"]]["cache_file"] == str(t["cache_shared_mesh"])
    assert by_run[t["shared_b_resp"]]["cache_file"] == str(t["cache_shared_resp"])
    assert by_run[t["single_mesh"]]["cache_file"] == str(t["single_cache_mesh"])


# ------------------------------------------------------------------ 6. near-miss prefix range


def test_prefix_range_excludes_near_miss_cache_names(tmp_path):
    """``abc`` must never pick ``abcd``: the bisect range stops before the near-miss."""
    cache = tmp_path / "cache" / "solve"
    payload = b"near-miss-bytes"
    for name in ("abc", "abcd", "abc-mnt-0123456789ab"):
        _write(cache / name / "response.npz", payload)
    # All three contain the filename, so only the name range can exclude ``abcd``.

    design = tmp_path / "runs" / "r1" / "designs" / "deadbeef"
    design.mkdir(parents=True)
    _write_json(design / "design.json", {"design_hash": "deadbeef"})
    _write_json(design / "status.json", {"ok": True, "key": "abc"})

    index = dedupe._CacheIndex(cache)
    assert index.with_prefix("abc-") == ["abc-mnt-0123456789ab"]

    candidates, have_metadata = dedupe._candidates(
        design, dedupe.KIND_SOLVE, cache, None, index=index
    )
    assert have_metadata is True
    assert [c.parent.name for c in candidates] == ["abc", "abc-mnt-0123456789ab"]
    assert "abcd" not in [c.parent.name for c in candidates]


# ------------------------------------------------- 7. shared cache entry hashed and linked once


def test_shared_cache_entry_is_hashed_once_and_both_runs_link(tmp_path, monkeypatch):
    """Two run dirs resolving to the same cache entry: one sha256, both linked."""
    t = _make_tree(tmp_path)
    manifest = tmp_path / "manifests" / "shared.json"
    cache_file = t["cache_shared_mesh"]

    calls: list[Path] = []
    original = dedupe.sha256_file

    def counting(path):
        calls.append(Path(path))
        return original(path)

    monkeypatch.setattr(dedupe, "sha256_file", counting)

    assert dedupe.main(_argv(t, manifest, "--apply")) == 0

    assert os.path.samefile(t["shared_a_mesh"], cache_file)
    assert os.path.samefile(t["shared_b_mesh"], cache_file)
    assert cache_file.stat().st_nlink == 3          # two runs + the cache entry
    assert len([p for p in calls if p == cache_file]) == 1

    doc = _load_manifest(manifest)
    by_run = {Path(e["run_file"]): e for e in doc["entries"]}
    assert by_run[t["shared_a_mesh"]]["cache_file"] == str(cache_file)
    assert by_run[t["shared_b_mesh"]]["cache_file"] == str(cache_file)
    assert by_run[t["shared_a_mesh"]]["action"] == "linked"
    assert by_run[t["shared_b_mesh"]]["action"] == "linked"
