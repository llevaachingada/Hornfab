"""Offline: ``verify --designs`` / ``--designs-file`` re-solve exactly the named hashes (lane B, 2026-10-31)."""
from __future__ import annotations

import pytest

from hornlab_search import cli
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture(autouse=True)
def _cold_worker_state():
    from hornlab_search.solve import worker
    worker.mark_cold()
    yield
    worker.mark_cold()


@pytest.fixture
def src(smoke_cfg, tmp_path, monkeypatch):
    install_fakes(monkeypatch, SyntheticBackend())
    run_dir = tmp_path / "runs" / "20261031T000000Z-screen-abcdef"
    cma_mod.search(fast_cfg(smoke_cfg), run_dir, "screen", backend=SyntheticBackend(), budget=6,
                   store=DatasetStore(tmp_path / "ds"), lib_shas=LIBS)
    ok = sorted((r for r in read_ndjson(run_dir / "search.ndjson") if r.get("ok")), key=lambda r: r["objective"])
    hashes = list(dict.fromkeys(r["design_hash"] for r in ok))
    assert len(hashes) >= 3
    return run_dir, hashes


def _verify(tmp_path, monkeypatch, run_dir, *extra):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    monkeypatch.setattr(cli, "_backend", lambda cfg: be)
    code = cli.main(["verify", "--run", str(run_dir), "--runs-dir", str(tmp_path / "runs"),
                     "--dataset-dir", str(tmp_path / "ds"), "--cache-dir", str(tmp_path / "cache"), *extra])
    return code, be


def _verified(run_dir):
    return [r["design_hash"] for r in read_ndjson(run_dir / "verify" / "search.ndjson")]


def test_designs_resolves_named_hashes_in_given_order(src, tmp_path, monkeypatch):
    run_dir, h = src
    pick = [h[2], h[0]]
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--designs", f"{pick[0]}, {pick[1]},{pick[0]}")
    assert code == 0 and be.calls == 2
    assert _verified(run_dir) == pick


def test_designs_file_csv(src, tmp_path, monkeypatch):
    run_dir, h = src
    f = tmp_path / "sel.csv"
    f.write_text(f"rank,design\n1,{h[1]}\n2,{h[2]}\n", encoding="utf-8")
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--designs-file", str(f))
    assert code == 0 and be.calls == 2
    assert _verified(run_dir) == [h[1], h[2]]


def test_unknown_hash_is_hard_error_listing_missing(src, tmp_path, monkeypatch, capsys):
    run_dir, h = src
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--designs", f"{h[0]},deadbeef0000,cafe1234")
    assert code == 2 and be.calls == 0
    out = capsys.readouterr().out
    assert "deadbeef0000" in out and "cafe1234" in out and h[0] not in out.split(":")[-1]
    assert not (run_dir / "verify" / "search.ndjson").exists()


def test_designs_file_without_design_column(src, tmp_path, monkeypatch, capsys):
    run_dir, h = src
    f = tmp_path / "bad.csv"
    f.write_text(f"hash\n{h[0]}\n", encoding="utf-8")
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--designs-file", str(f))
    assert code == 2 and be.calls == 0 and "'design' column" in capsys.readouterr().out


def test_top_default_still_five_and_flags_exclusive(src, tmp_path, monkeypatch):
    run_dir, h = src
    code, be = _verify(tmp_path, monkeypatch, run_dir)
    assert code == 0 and be.calls == min(5, len(h))
    code, _ = _verify(tmp_path, monkeypatch, run_dir, "--top", "2", "--designs", h[0])
    assert code == 2
    code, _ = _verify(tmp_path, monkeypatch, run_dir, "--designs", h[0], "--designs-file", "x.csv")
    assert code == 2


# -- backend-aware output dirs (fix/verify-backend-dir, 2026-11-12) ---------------------------
# A CPU verify must never write into the source run's verify/ dir that a GPU verify owns: the
# response.npz/metrics.json would be overwritten and lane parity would become unmeasurable.

def _run_json(run_dir):
    from hornlab_search.search.rundir import read_json
    return read_json(run_dir / "run.json", {}) or {}


def test_backend_override_writes_its_own_run_dir(src, tmp_path, monkeypatch):
    run_dir, h = src
    assert _run_json(run_dir).get("backend") == "beat_cuda"
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--backend", "beat_cpu", "--top", "2")
    assert code == 0 and be.calls == 2
    assert not (run_dir / "verify" / "search.ndjson").exists()
    dirs = [p for p in (tmp_path / "runs").glob("*-verify-*") if p.is_dir()]
    assert len(dirs) == 1
    meta = _run_json(dirs[0])
    assert meta["backend"] == "beat_cpu" and meta["mode"] == "verify"
    assert meta["verify_of"]["backend"] == "beat_cpu"
    assert meta["verify_of"]["run"].replace("\\", "/").rsplit("/", 1)[-1] == run_dir.name
    assert len(read_ndjson(dirs[0] / "search.ndjson")) == 2


def test_verify_dir_flag_writes_exactly_there(src, tmp_path, monkeypatch):
    run_dir, h = src
    out = tmp_path / "cpu_verify"
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--backend", "beat_cpu",
                       "--verify-dir", str(out), "--top", "2")
    assert code == 0 and be.calls == 2
    assert len(read_ndjson(out / "search.ndjson")) == 2
    assert not (run_dir / "verify" / "search.ndjson").exists()
    assert not list((tmp_path / "runs").glob("*-verify-*"))


def test_explicit_verify_dir_refuses_a_mixed_backend(src, tmp_path, monkeypatch, capsys):
    run_dir, h = src
    out = tmp_path / "mixed"
    out.mkdir()
    (out / "search.ndjson").write_text(
        '{"ok": true, "design_hash": "deadbeef0000", "backend": "beat_cuda"}\n', encoding="utf-8")
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--backend", "beat_cpu",
                       "--verify-dir", str(out))
    assert code == 2 and be.calls == 0
    assert "already holds rows from backend" in capsys.readouterr().out


def test_same_backend_override_keeps_the_source_verify_dir(src, tmp_path, monkeypatch):
    run_dir, h = src
    stored = _run_json(run_dir)["backend"]
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--backend", stored, "--top", "2")
    assert code == 0 and be.calls == 2
    assert len(read_ndjson(run_dir / "verify" / "search.ndjson")) == 2
    assert not list((tmp_path / "runs").glob("*-verify-*"))
