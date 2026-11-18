"""Regression for the lane-C `import_results` hook (applied 2026-11-18 from NOTES_FOR_SENIOR).

`detect_result_artifact` now classifies a BL headless result DIRECTORY before file suffix
checks, and `read_headless_result` delegates to the typed reader without duplicating payload
parsing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system.boundarylab import import_results as IR  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"


def test_detect_classifies_a_bl_headless_result_directory() -> None:
    artifact = IR.detect_result_artifact(FIXTURE)
    assert artifact.kind == "bl_headless_result"
    assert artifact.manifest is None
    assert "read_bl_headless_result" in artifact.notes[0]


def test_detect_unknown_directory_stays_unknown_without_crashing(tmp_path: Path) -> None:
    empty = tmp_path / "empty_dir"
    empty.mkdir()
    artifact = IR.detect_result_artifact(empty)
    assert artifact.kind == "unknown"


def test_detect_file_branches_unchanged(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        IR.detect_result_artifact(tmp_path / "nope")


def test_read_headless_result_delegates_to_the_typed_reader() -> None:
    result = IR.read_headless_result(FIXTURE)
    assert result.data_quality["quality"] == "EXACT_COMPLEX"
    assert result.excitation_ids
    assert len(result.frequencies_hz) > 0
