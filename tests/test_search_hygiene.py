"""Tests for hornlab_search.search.hygiene (offline, no GPU, all subprocess mocked)."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from hornlab_search.search.hygiene import (
    _cmdline_matches,
    _is_windows,
    clear_julia,
    hygiene_snapshot,
    list_project_julia,
    vram_used_mib,
)


# ------------------------------------------------------------------ _cmdline_matches


def test_cmdline_matches_hornlab():
    assert _cmdline_matches("/path/to/julia /home/user/hornlab/beat_server.jl")


def test_cmdline_matches_beat():
    assert _cmdline_matches("julia.exe --project=C:\\Users\\beat_engine.jl beat_worker")


def test_cmdline_matches_case_insensitive():
    assert _cmdline_matches("julia.exe HORNLAB_BEAT main.jl")
    assert _cmdline_matches("julia /usr/local/HornLab/server.jl")


def test_cmdline_does_not_match_other():
    assert not _cmdline_matches("julia.exe /home/user/other_project/audio.jl")
    assert not _cmdline_matches("julia /tmp/test_run.jl")
    assert not _cmdline_matches("")


def test_cmdline_does_not_match_unrelated():
    # Should NOT kill Julia processes for unrelated projects
    assert not _cmdline_matches("julia.exe /other_company/sound_tool/server.jl")
    assert not _cmdline_matches("julia /usr/share/music/synth.jl")


# ------------------------------------------------------------------ clear_julia


def test_clear_julia_only_kills_matching(monkeypatch):
    """clear_julia must skip processes without project keywords in cmdline."""
    killed = []

    def mock_run(args, **kw):
        # Capture taskkill /F /PID <pid>
        if "taskkill" in str(args):
            for i, a in enumerate(args):
                if a == "/PID" and i + 1 < len(args):
                    killed.append(int(args[i + 1]))
        return MagicMock(returncode=0)

    procs = [
        {"pid": 1001, "cmdline": "julia.exe /hornlab/beat_server.jl"},
        {"pid": 1002, "cmdline": "julia.exe /other/unrelated.jl"},    # must NOT be killed
        {"pid": 1003, "cmdline": "julia beat_worker.jl"},
    ]
    import hornlab_search.search.hygiene as hyg_mod
    # Force Windows path (taskkill) so the test works on both platforms
    with patch.object(hyg_mod, "_is_windows", return_value=True), \
         patch("subprocess.run", side_effect=mock_run):
        result = clear_julia(procs=procs)

    assert 1001 in result
    assert 1003 in result
    assert 1002 not in result  # must not kill non-project process


def test_clear_julia_returns_killed_pids(monkeypatch):
    import hornlab_search.search.hygiene as hyg_mod
    with patch.object(hyg_mod, "_is_windows", return_value=True), \
         patch("subprocess.run", return_value=MagicMock(returncode=0)):
        result = clear_julia(procs=[{"pid": 999, "cmdline": "julia /hornlab/server.jl"}])
    assert 999 in result


def test_clear_julia_empty_list():
    assert clear_julia(procs=[]) == []


def test_clear_julia_skips_nonmatching():
    """When all processes are non-matching, nothing is killed."""
    import hornlab_search.search.hygiene as hyg_mod
    with patch.object(hyg_mod, "_is_windows", return_value=True), \
         patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        result = clear_julia(procs=[{"pid": 555, "cmdline": "julia /other/code.jl"}])
    assert result == []
    mock_run.assert_not_called()


# ------------------------------------------------------------------ vram_used_mib


def test_vram_used_mib_returns_float_on_success(monkeypatch):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "3456\n"
    with patch("subprocess.run", return_value=mock_result):
        v = vram_used_mib()
    assert v == 3456.0


def test_vram_used_mib_returns_none_on_missing_tool(monkeypatch):
    with patch("subprocess.run", side_effect=FileNotFoundError("nvidia-smi not found")):
        v = vram_used_mib()
    assert v is None


def test_vram_used_mib_returns_none_on_nonzero_returncode(monkeypatch):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        v = vram_used_mib()
    assert v is None


def test_vram_used_mib_returns_none_on_parse_error(monkeypatch):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "not a number\n"
    with patch("subprocess.run", return_value=mock_result):
        v = vram_used_mib()
    assert v is None


# ------------------------------------------------------------------ list_project_julia (mocked)


def test_list_project_julia_returns_only_matching(monkeypatch):
    """list_project_julia on POSIX returns only processes with project keywords.

    ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND (11+ columns).
    """
    # Build lines with proper ps aux format (at least 11 columns, cmd is col 10)
    def _ps_line(user, pid, cmd):
        return f"{user}  {pid}  0.0  0.1  12345  6789  ?  S  10:00  0:00  {cmd}"

    ps_output = "\n".join([
        _ps_line("user", 1111, "julia /hornlab/beat.jl"),
        _ps_line("user", 1112, "julia /other/project.jl"),
        _ps_line("user", 1113, "julia beat_server.jl"),
    ]) + "\n"
    mock_result = MagicMock()
    mock_result.stdout = ps_output
    import hornlab_search.search.hygiene as hyg_mod
    with patch.object(hyg_mod, "_is_windows", return_value=False), \
         patch("subprocess.run", return_value=mock_result):
        procs = list_project_julia()
    pids = [p["pid"] for p in procs]
    assert 1111 in pids
    assert 1113 in pids
    assert 1112 not in pids


# ------------------------------------------------------------------ hygiene_snapshot


def test_hygiene_snapshot_structure(monkeypatch):
    """hygiene_snapshot returns expected keys."""
    with patch("hornlab_search.search.hygiene.list_project_julia", return_value=[]), \
         patch("hornlab_search.search.hygiene.vram_used_mib", return_value=512.0):
        snap = hygiene_snapshot("test-label")
    assert snap["label"] == "test-label"
    assert "julia_project_procs" in snap
    assert "vram_used_mib" in snap
    assert snap["vram_used_mib"] == 512.0
