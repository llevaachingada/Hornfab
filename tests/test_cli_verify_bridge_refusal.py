"""``verify`` refuses opt-in bridge-cell runs before any GPU/solver work."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from hornlab_search import cli


def _run_dir(tmp_path, rows_type="rosse_rect"):
    run = tmp_path / "20261119T085256Z-screen-c2203f"
    run.mkdir()
    (run / "config.yaml").write_text(
        "generator:\n"
        "  name: grid\n"
        "  rows:\n"
        f"    type: {rows_type}\n",
        encoding="utf-8",
    )
    row = {"n": 0, "design_hash": "a23108469464", "ok": True, "objective": 4.8907}
    (run / "search.ndjson").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return run


def test_bridge_helper_names_type_entry_point_and_replacement_command(tmp_path):
    run = _run_dir(tmp_path)
    msg = cli._bridge_rows_refusal(run / "config.yaml", run, "a23108469464",
                                   tmp_path / "verify_out")
    assert msg is not None
    assert "rowse_rect" in msg or "rosse_rect" in msg
    assert "tools/geometry/rosse_rect_cli.py" in msg
    assert "python tools/geometry/rosse_rect_cli.py verify --run" in msg
    assert "--designs a23108469464" in msg
    assert "--verify-dir" in msg


def test_helper_is_none_for_stock_rows(tmp_path):
    run = _run_dir(tmp_path, rows_type="lecleach")
    assert cli._bridge_rows_refusal(run / "config.yaml", run, "h") is None


def test_verify_body_refuses_before_solver_and_never_creates_output(tmp_path, monkeypatch, capsys):
    run = _run_dir(tmp_path)
    out = tmp_path / "should_not_exist"
    args = SimpleNamespace(run=str(run), verify_dir=str(out), designs=None,
                           designs_file=None, top=1, brief=None, backend=None)

    from hornlab_search.solve import worker

    def _solver_touched(*_a, **_k):
        raise AssertionError("verify reached the solver for a bridge cell")

    monkeypatch.setattr(worker, "warm", _solver_touched)
    code = cli._verify_body(args, ["verify", "--run", str(run)], {})
    assert code == 2
    text = capsys.readouterr().out
    assert "verify REFUSED" in text
    assert "rosse_rect" in text
    assert "tools/geometry/rosse_rect_cli.py" in text
    assert "python tools/geometry/rosse_rect_cli.py verify --run" in text
    assert not out.exists()
