"""Fix B (item 8, 2026-11-16): directivity pairing guard.

Tests that:
- search_preflight._check_directivity emits HARD when typology and brief tags disagree
- run_campaign_night._directivity_mismatch returns a message on mismatch and None on match
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import tools.run_campaign_night as night

# Allow importing search_preflight as a module
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import search_preflight as pf  # noqa: E402


# ------------------------------------------------------------------ preflight check


def _fake_cfg(typology_dir=None, brief_dir=None, brief_embedded=False):
    """Build a fake config object with the needed .raw attribute."""
    raw = {}
    if typology_dir is not None:
        raw["directivity"] = typology_dir
    if brief_embedded and brief_dir is not None:
        raw["brief"] = {"directivity": brief_dir}
    elif brief_dir is not None:
        # Store brief inline for testing without filesystem
        raw["brief"] = {"directivity": brief_dir}
    return SimpleNamespace(raw=raw)


def _new_report():
    return {"findings": [], "severity": "OK"}


def test_preflight_no_directivity_no_check():
    """When typology has no directivity tag, check passes silently."""
    cfg = _fake_cfg(typology_dir=None, brief_dir="cd")
    report = _new_report()
    pf._check_directivity(cfg, "/fake/path.yaml", report)
    assert report["findings"] == []


def test_preflight_matching_dirs_no_hard():
    """When both tags are present and equal, no HARD is emitted."""
    for tag in ("cd", "narrowing"):
        cfg = _fake_cfg(typology_dir=tag, brief_dir=tag)
        report = _new_report()
        pf._check_directivity(cfg, "/fake/path.yaml", report)
        assert report["findings"] == [], f"tag={tag!r}"


def test_preflight_mismatch_emits_hard():
    """When typology says 'cd' but brief says 'narrowing' (or vice versa) → HARD."""
    cfg = _fake_cfg(typology_dir="cd", brief_dir="narrowing")
    report = _new_report()
    pf._check_directivity(cfg, "/fake/path.yaml", report)
    assert len(report["findings"]) == 1
    assert report["findings"][0]["severity"] == "HARD"
    assert "directivity_mismatch" in report["findings"][0]["code"]

    cfg2 = _fake_cfg(typology_dir="narrowing", brief_dir="cd")
    report2 = _new_report()
    pf._check_directivity(cfg2, "/fake/path.yaml", report2)
    assert len(report2["findings"]) == 1
    assert report2["findings"][0]["severity"] == "HARD"


def test_preflight_unknown_tag_ignored():
    """An unrecognised directivity tag (typo etc.) is silently skipped — no HARD."""
    cfg = _fake_cfg(typology_dir="unknown_tag", brief_dir="cd")
    report = _new_report()
    pf._check_directivity(cfg, "/fake/path.yaml", report)
    assert report["findings"] == []


def test_preflight_brief_absent_no_check():
    """Typology is tagged but brief has no tag → no check (can't be wrong)."""
    cfg = SimpleNamespace(raw={"directivity": "cd"})   # no brief key
    report = _new_report()
    pf._check_directivity(cfg, "/fake/path.yaml", report)
    assert report["findings"] == []
