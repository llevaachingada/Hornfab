"""Offline tests for :mod:`hornlab_search.system.paths` (contract section 1).

Pure string tests: Windows and POSIX inputs must behave identically on every OS.
"""
from __future__ import annotations

from hornlab_search.system import paths


def test_split_any_windows_and_posix_are_identical():
    assert paths.split_any(r"C:\a\b\mesh.msh") == ("a", "b", "mesh.msh")
    assert paths.split_any("C:/a/b/mesh.msh") == ("a", "b", "mesh.msh")
    assert paths.split_any(r"C:\a\b\mesh.msh") == paths.split_any("/a/b/mesh.msh")


def test_split_any_drops_empty_parts_and_drive():
    assert paths.split_any("C:") == ()
    assert paths.split_any(r"\\server\share\x") == ("server", "share", "x")
    assert paths.split_any("/a//b/") == ("a", "b")


def test_leaf_dir_name_is_os_agnostic():
    assert paths.leaf_dir_name(r"C:\a\b\mesh.msh") == "b"
    assert paths.leaf_dir_name("/a/b/mesh.msh") == "b"
    assert paths.leaf_dir_name(
        "C:\\Users\\x\\lecleach_rollback_1in_v6_9e02db06ecc3\\mesh.msh"
    ) == "lecleach_rollback_1in_v6_9e02db06ecc3"
    assert paths.leaf_dir_name("mesh.msh") is None


def test_to_store_relative_windows_store_root_and_marker():
    # explicit, separator-agnostic hint (the normal reader path)
    assert paths.to_store_relative(
        "C:/Users/x/system_runs/system/e/c/run/manifest.json",
        ["C:\\Users\\x\\system_runs"],
    ) == "system/e/c/run/manifest.json"
    # case-insensitive hint
    assert paths.to_store_relative(
        "c:/users/X/SYSTEM_RUNS/system/e/c",
        ["C:/Users/x/system_runs"],
    ) == "system/e/c"
    # the system_runs marker alone anchors the store root
    assert paths.to_store_relative(
        "C:/Users/x/system_runs/system/e/c/run/manifest.json", []
    ) == "system/e/c/run/manifest.json"
    assert paths.to_store_relative(
        "C:/Users/x/system_runs/system/e/c/run/manifest.json", ("unrelated",)
    ) == "system/e/c/run/manifest.json"


def test_to_store_relative_no_match_is_none():
    assert paths.to_store_relative("/elsewhere/file.json", ["/tmp/store"]) is None
    assert paths.to_store_relative("", []) is None


def test_helpers_are_deterministic():
    first = paths.to_store_relative("C:/x/system_runs/system/e/c", [])
    second = paths.to_store_relative("C:/x/system_runs/system/e/c", [])
    assert first == second == "system/e/c"
