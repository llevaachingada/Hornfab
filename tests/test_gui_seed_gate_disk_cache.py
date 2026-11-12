"""WP2b (GUI plan 2026-11-12): the list_configs seed gate persists to a per-user cache file,
keyed on config+brief stamps AND a code fingerprint, so a restart is instant but a code or
config edit re-materializes. Offline: synthetic examples tree, the march is monkeypatched."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D


@pytest.fixture()
def tree(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    ex = root / "examples"
    ex.mkdir(parents=True)
    (ex / "a.yaml").write_text(yaml.safe_dump({"name": "a", "family": "OSSE"}))
    (ex / "b.yaml").write_text(yaml.safe_dump({"name": "b", "family": "OSSE"}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "cache"))
    monkeypatch.delenv("HORNLAB_GUI_NO_DISK_CACHE", raising=False)
    monkeypatch.setenv("HORNLAB_GUI_DISK_CACHE_IN_TESTS", "1")
    calls: list[str] = []
    monkeypatch.setattr(D, "_config_seed_materializes", lambda p: calls.append(p.name) or p.name == "a.yaml")
    monkeypatch.setattr(D, "catalog", lambda root: [])

    def fresh_process():                      # what a GUI restart clears
        D._SEED_GATE_CACHE.clear()
        D._SEED_DISK = None
        D._SEED_DISK_DIRTY = False

    fresh_process()
    yield root, calls, fresh_process
    fresh_process()
    D._CODE_STAMP = None


def _disabled(root):
    return {c["name"]: c.get("disabled") for c in D.list_configs(root)}


def test_restart_reads_disk_not_march(tree):
    root, calls, restart = tree
    first = _disabled(root)
    assert sorted(calls) == ["a.yaml", "b.yaml"]
    restart()
    calls.clear()
    assert _disabled(root) == first and calls == []          # served from the cache file


def test_config_edit_rematerializes_only_that_config(tree):
    root, calls, restart = tree
    _disabled(root)
    p = root / "examples" / "b.yaml"
    p.write_text(p.read_text() + "\n# edited\n")
    t = time.time() + 5
    os.utime(p, (t, t))
    restart()
    calls.clear()
    _disabled(root)
    assert calls == ["b.yaml"]


def test_code_change_invalidates_everything(tree, monkeypatch):
    root, calls, restart = tree
    _disabled(root)
    restart()
    calls.clear()
    monkeypatch.setattr(D, "_CODE_STAMP", "different-code")
    _disabled(root)
    assert sorted(calls) == ["a.yaml", "b.yaml"]


def test_env_switch_disables_persistence(tree, monkeypatch):
    root, calls, restart = tree
    monkeypatch.setenv("HORNLAB_GUI_NO_DISK_CACHE", "1")
    _disabled(root)
    restart()
    calls.clear()
    _disabled(root)
    assert sorted(calls) == ["a.yaml", "b.yaml"]
