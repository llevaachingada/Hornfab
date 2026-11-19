"""resolve_warm_runs: @design placeholders become the newest run holding that design."""
import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[1] / "tools/night_queue/resolve_warm_runs.py"
_spec = importlib.util.spec_from_file_location("resolve_warm_runs", _p)
RW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RW)


def _run(root, name, h, ndjson=True):
    d = root / name / "designs" / h
    d.mkdir(parents=True)
    if ndjson:
        (root / name / "search.ndjson").write_text("{}\n")


def test_placeholder_resolves_to_newest_run_and_missing_is_reported(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "20261101T000000Z-screen-a", "abc123")
    _run(runs, "20261102T000000Z-screen-b", "abc123")
    _run(runs, "20261103T000000Z-screen-c", "abc123", ndjson=False)   # no rows: ignored
    cfg = tmp_path / "c.yaml"
    cfg.write_text("search:\n  warm_start:\n    from_runs: [runs/@design:abc123, runs/nope]\n")
    r = RW.resolve_file(cfg, runs)
    assert r["resolved"] == {"abc123": "runs/20261102T000000Z-screen-b"}
    assert r["missing"] == ["runs/nope"] and r["unresolved"] == []
    assert "runs/20261102T000000Z-screen-b" in cfg.read_text()


def test_unknown_design_stays_and_is_flagged(tmp_path):
    (tmp_path / "runs").mkdir()
    cfg = tmp_path / "c.yaml"
    cfg.write_text("search:\n  warm_start:\n    from_runs: [runs/@design:ffff00]\n")
    r = RW.resolve_file(cfg, tmp_path / "runs", write=False)
    assert r["unresolved"] == ["ffff00"]


def _study_run(root, study, mode, h, ndjson=True):
    d = root / study / mode / "designs" / h
    d.mkdir(parents=True)
    if ndjson:
        (root / study / mode / "search.ndjson").write_text("{}\n")


def test_study_layout_screen_and_verify_resolve(tmp_path):
    """2026-11-19: the owner box nests run dirs as runs/<study>/<screen|verify>/designs/<hash>;
    the one-level glob left those placeholders unresolved."""
    runs = tmp_path / "runs"
    _study_run(runs, "study-aaaaaaaaaaaa", "screen", "abc123")
    _study_run(runs, "study-bbbbbbbbbbbb", "verify", "abc123")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("search:\n  warm_start:\n    from_runs: [runs/@design:abc123]\n")
    r = RW.resolve_file(cfg, runs)
    # both layouts are eligible; the verify dir (written second) is the newest
    assert r["unresolved"] == [] and r["missing"] == []
    assert r["resolved"] == {"abc123": "runs/study-bbbbbbbbbbbb/verify"}

    only_screen = tmp_path / "runs2"
    _study_run(only_screen, "study-cccccccccccc", "screen", "def456")
    cfg2 = tmp_path / "d.yaml"
    cfg2.write_text("search:\n  warm_start:\n    from_runs: [runs/@design:def456]\n")
    r2 = RW.resolve_file(cfg2, only_screen)
    assert r2["resolved"] == {"def456": "runs/study-cccccccccccc/screen"}
