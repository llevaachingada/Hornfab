"""Overview phase 4 (WP4.2): the CPU-only ``overview-snapshot`` job kind.

Headless and offline: synthetic run/analysis trees; the two child processes are monkeypatched, so
no analysis tool actually runs and nothing is solved.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yaml

from hornlab_search.gui import data_overview_snapshot as S
from hornlab_search.gui.jobs import SNAPSHOT_ENTRY, JobManager


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    (runs / "analysis").mkdir(parents=True)
    return root, runs


def test_snapshot_is_a_cpu_kind_with_its_own_entry(tmp_path):
    root, runs = _repo(tmp_path)
    jm = JobManager(root, runs)
    argv, gpu = jm.build_argv("overview-snapshot", {"days": 7})
    assert gpu is False and argv == ["--days", "7.0"]
    assert jm._entry_for("overview-snapshot", argv) == SNAPSHOT_ENTRY
    assert jm.preview("overview-snapshot", {})["command"].startswith("python " + SNAPSHOT_ENTRY)


def test_snapshot_refuses_bad_days(tmp_path):
    root, runs = _repo(tmp_path)
    jm = JobManager(root, runs)
    for bad in ("nope", 0, 400):
        try:
            jm.build_argv("overview-snapshot", {"days": bad})
        except ValueError as exc:
            assert "days" in str(exc)
        else:                                       # pragma: no cover - a silent pass is the defect
            raise AssertionError(f"days={bad!r} was accepted")


def test_snapshot_main_builds_spec_then_report(tmp_path, monkeypatch):
    root, _ = _repo(tmp_path)
    calls: list[list[str]] = []

    class _Done:
        returncode = 0

    def fake_run(argv, **kw):
        calls.append(list(argv))
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)      # report_day would create it
        (out / "report_day.json").write_text(json.dumps({"sections": [], "n_errors": 0}),
                                             encoding="utf-8")
        return _Done()

    monkeypatch.setattr(S.subprocess, "run", fake_run)
    rc = S.snapshot_main(["--days", "3"], root=root)
    assert rc == 0 and len(calls) == 2
    spec, report = Path(calls[0][calls[0].index("--out") + 1]), Path(calls[1][calls[1].index("--out") + 1])
    assert spec.name == "spec.yaml" and spec.parent == report
    assert report.name == f"overview_{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"
    assert report.parent == root / "runs" / "analysis"
    # a second snapshot on the same day never overwrites the first
    assert S.snapshot_main(["--days", "3"], root=root) == 0
    assert calls[2][calls[2].index("--out") + 1] != str(report)


def test_snapshots_lists_frozen_reports_newest_first(tmp_path):
    root, runs = _repo(tmp_path)
    for name, errs in (("overview_2026-11-18", 1), ("overview_2026-11-19", 0)):
        d = runs / "analysis" / name
        d.mkdir()
        (d / "report_day.json").write_text(
            json.dumps({"generated_utc": "2026-11-19T00:00:00Z",
                        "sections": [{"status": "ok"}, {"status": "error" if errs else "ok"}],
                        "n_errors": errs}), encoding="utf-8")
        (d / "spec.yaml").write_text(yaml.safe_dump({"runs_root": "runs"}), encoding="utf-8")
    (runs / "analysis" / "not_a_snapshot").mkdir()
    out = S.snapshots(root, runs)
    assert [s["id"] for s in out] == ["overview_2026-11-19", "overview_2026-11-18"]
    assert out[1]["n_errors"] == 1 and out[0]["n_errors"] == 0
    assert out[0]["href"] == "#/analysis/overview_2026-11-19" and out[0]["spec"] is True
    assert S.snapshots(root, tmp_path / "missing") == []
