"""Tests 24-28 of 08_TASK_PIPELINE against the REAL stack (mesher + BEAT on the GPU).

Run: .venv/Scripts/python.exe -m pytest tests/test_end_to_end.py -v -m slow

Hygiene (AGENTS.md): the module starts from a clean Julia state, runs one solver process at a time
(the CLI runs in-process, sharing one warm host), and verifies the host is gone at the end.
"""
from __future__ import annotations

import json

import pytest

from conftest import EXAMPLES, requires_beat, requires_mesher
from hornlab_search import cli
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.solve import worker
from test_solve_support import clean_host_state, release_and_verify

pytestmark = [requires_beat, requires_mesher, pytest.mark.slow]


@pytest.fixture(scope="module")
def sandbox(tmp_path_factory):
    state = clean_host_state()
    assert state["hosts_left"] == [], state
    root = tmp_path_factory.mktemp("e2e")
    yield {"root": root, "dirs": ["--runs-dir", str(root / "runs"), "--cache-dir", str(root / "cache"),
                                  "--dataset-dir", str(root / "dataset")], "runs": []}
    worker.uninstall_handlers()
    end = release_and_verify()
    assert end["hosts_left"] == [], end


def go(*argv):
    return cli.main(list(argv))


def newest(sb):
    return sorted((sb["root"] / "runs").iterdir())[-1]


# 24
def test_24_run_baseline_screen(sandbox, capsys):
    rc = go("run", "--config", str(EXAMPLES / "osse_baseline.yaml"), "--mode", "screen", "-v",
            *sandbox["dirs"])
    capsys.readouterr()
    assert rc == 0
    run_dir = newest(sandbox)
    (design,) = (run_dir / "designs").iterdir()
    for f in ("response.npz", "metrics.json", "status.json"):
        assert (design / f).exists(), f
    assert len(DatasetStore(sandbox["root"] / "dataset")) == 1
    metrics = json.loads((design / "metrics.json").read_text())
    assert metrics["di_source"] == "balloon"


# 25
def test_25_search_smoke_budget_8(sandbox, capsys):
    rc = go("search", "--config", str(EXAMPLES / "search_smoke.yaml"), "--budget", "8", "-v",
            *sandbox["dirs"])
    capsys.readouterr()
    assert rc == 0
    run_dir = newest(sandbox)
    sandbox["runs"].append(run_dir)
    assert len(read_ndjson(run_dir / "search.ndjson")) == 8
    assert (run_dir / "best.json").exists()
    assert len(DatasetStore(sandbox["root"] / "dataset")) == 1 + 8


# 26
def test_26_report(sandbox, capsys):
    run_dir = sandbox["runs"][-1]
    rc = go("report", str(run_dir), "--out", str(sandbox["root"] / "report.html"))
    capsys.readouterr()
    assert rc == 0 and (sandbox["root"] / "report.html").stat().st_size > 20_000


# 27
def test_27_dry_run_makes_no_solver_call(sandbox, monkeypatch, capsys):
    from hornlab_search.solve.beat import BeatBackend

    def forbidden(*a, **k):
        raise AssertionError("dry-run called backend.solve")
    monkeypatch.setattr(BeatBackend, "solve", forbidden)
    monkeypatch.setattr(BeatBackend, "solve_traced", forbidden)
    rc = go("run", "--config", str(EXAMPLES / "osse_baseline.yaml"), "--dry-run")
    out = capsys.readouterr().out
    assert rc == 0 and "no solver was launched" in out


# 28
def test_28_dataset_stats(sandbox, capsys):
    rc = go("dataset", "stats", *sandbox["dirs"])
    out = capsys.readouterr().out
    assert rc == 0 and "dataset stats OK: 9 records" in out
