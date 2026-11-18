"""Boundary Lab probe tests (fake BL trees under tmp_path; read-only on the real machine)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system.boundarylab import probe as P  # noqa: E402

REQUIRED = list(P.REQUIRED_CHECKOUT_FILES)


def _make_fake_bl(tmp_path: Path, *, name: str = "boundary-lab",
                  venv: bool = True, cli: bool = True) -> Path:
    root = tmp_path / name
    for relative in REQUIRED:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture file\n", encoding="utf-8")
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "boundary-lab"\nversion = "9.9.9"\n'
        '[project.scripts]\nblab = "blab.cli:main"\n', encoding="utf-8")
    (root / "geometry_providers" / "vented_enclosure" / "provider.json").write_text(
        json_manifest(), encoding="utf-8")
    if venv:
        scripts = root / ".venv" / "Scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "python.exe").write_text("", encoding="utf-8")  # existence is what probe checks
        if cli:
            (scripts / "blab.exe").write_text("", encoding="utf-8")
    return root


def json_manifest() -> str:
    return (
        '{"manifest_version":1,"id":"blab.vented_enclosure","provider_api":1,'
        '"backend":"enclosure.backend:create_backend",'
        '"default_source":{"width_m":0.32} }'
    )


def test_probe_finds_and_verifies_fake_checkout(tmp_path: Path) -> None:
    root = _make_fake_bl(tmp_path)
    result = P.probe_boundarylab(extra_roots=[str(root)], use_default_roots=False)
    assert result.found is True
    assert result.status == P.BL_CAPABILITY_OK
    verified = result.verified_root
    assert verified is not None and verified.verified
    assert verified.kind == "checkout"
    assert verified.version == "9.9.9"
    assert verified.python_executable is not None and verified.cli_entry is not None
    assert verified.detail["provider_manifest"]["id"] == "blab.vented_enclosure"


def test_probe_reports_missing_capability_on_empty_tree(tmp_path: Path) -> None:
    empty = tmp_path / "not_bl"
    empty.mkdir()
    result = P.probe_boundarylab(extra_roots=[str(empty)], use_default_roots=False)
    assert result.found is False
    assert result.status == P.BL_CAPABILITY_MISSING
    assert result.capability_missing == (
        result.capability_missing[0],) and "no Boundary Lab checkout" in result.capability_missing[0]


def test_probe_incomplete_checkout_lists_every_missing_file(tmp_path: Path) -> None:
    root = _make_fake_bl(tmp_path, venv=False, cli=False)
    (root / "src" / "blab" / "headless.py").unlink()
    result = P.probe_boundarylab(extra_roots=[str(root)], use_default_roots=False)
    assert result.found is True
    best = cast(P.BLRoot, result.verified_root) if result.verified_root else result.roots[0]
    assert best.verified is False
    assert best.status == P.BL_CAPABILITY_MISSING
    reasons = " | ".join(best.missing)
    assert "src/blab/headless.py" in reasons
    assert ".venv/Scripts/python.exe" in reasons
    assert "blab.exe" in reasons or "blab console entry" in reasons


def test_probe_is_read_only_over_two_runs(tmp_path: Path) -> None:
    root = _make_fake_bl(tmp_path)
    before = _tree_digest(root)
    first = P.probe_boundarylab(extra_roots=[str(root)], use_default_roots=False)
    second = P.probe_boundarylab(extra_roots=[str(root)], use_default_roots=False)
    after = _tree_digest(root)
    assert before == after, "probe must not write anything"
    assert first.to_dict() == second.to_dict(), "probe result must be deterministic"


def _tree_digest(root: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_boundary_lab_home_env_root_is_used(tmp_path: Path, monkeypatch) -> None:
    root = _make_fake_bl(tmp_path)
    monkeypatch.setenv("BOUNDARY_LAB_HOME", str(root))
    monkeypatch.setattr(P, "_default_candidate_roots", lambda: [Path(os.environ["BOUNDARY_LAB_HOME"])])
    result = P.probe_boundarylab(extra_roots=[], use_default_roots=True)
    assert result.found is True
    assert result.verified_root is not None
    assert Path(result.verified_root.path) == root.resolve()


def test_real_machine_probe_matches_baselined_facts() -> None:
    """On the dev machine the real install must be found and verified (BASELINE.md facts).

    Skips cleanly when Boundary Lab is absent so CI stays green.
    """
    pytest_import()
    import pytest  # local import keeps the module importable everywhere

    result = P.probe_boundarylab(extra_roots=["C:/Users/hunte/Github/boundary-lab"],
                                 use_default_roots=False)
    if not result.verified_root:
        pytest.skip("real Boundary Lab checkout not present/verified on this machine")
    verified = result.verified_root
    assert verified.kind == "checkout"
    assert verified.version is not None
    assert verified.python_executable and Path(verified.python_executable).is_file()
    assert verified.cli_entry and Path(verified.cli_entry).is_file()
    manifest = verified.detail["provider_manifest"]
    assert manifest["id"] == "blab.vented_enclosure"
    assert manifest["backend"] == "enclosure.backend:create_backend"


def pytest_import() -> None:  # helper keeps flake8 import order happy without top-level pytest
    return None
