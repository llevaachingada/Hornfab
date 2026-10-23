"""Offline: ``verify --brief`` applies the brief (it was parsed and ignored until 2026-10-23) and
writes its own run directory, so a 12 kHz verify (NEXT_DEV_PRIORITIES P2) never mixes with the
source run's 5.5 kHz rows."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search import cli
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

BRIEF_12K = Path(__file__).resolve().parents[1] / "examples" / "briefs" / "hifi_90x60_1in_12k.yaml"


@pytest.fixture(autouse=True)
def _cold_worker_state():
    from hornlab_search.solve import worker
    worker.mark_cold()
    yield
    worker.mark_cold()


def _source_run(smoke_cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    run_dir = tmp_path / "runs" / "20261023T000000Z-screen-abcdef"
    cma_mod.search(fast_cfg(smoke_cfg), run_dir, "screen", backend=be, budget=6,
                   store=DatasetStore(tmp_path / "ds"), lib_shas=LIBS)
    return run_dir, be


def _verify(tmp_path, monkeypatch, run_dir, *extra):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    monkeypatch.setattr(cli, "_backend", lambda cfg: be)
    code = cli.main(["verify", "--run", str(run_dir), "--top", "2", "--runs-dir", str(tmp_path / "runs"),
                     "--dataset-dir", str(tmp_path / "ds"), "--cache-dir", str(tmp_path / "cache"), *extra])
    return code, be


def test_verify_brief_uses_the_brief_band_and_writes_its_own_run(smoke_cfg, tmp_path, monkeypatch):
    run_dir, _ = _source_run(smoke_cfg, tmp_path, monkeypatch)
    before = {p.name for p in (tmp_path / "runs").iterdir()}
    brief = tmp_path / "brief_12k.yaml"                          # the fake mesh is 600 mm wide
    brief.write_text(BRIEF_12K.read_text(encoding="utf-8").replace("400.0", "1000.0").replace("300.0", "1000.0")
                     .replace("220.0", "1000.0"),
                     encoding="utf-8")
    code, be = _verify(tmp_path, monkeypatch, run_dir, "--brief", str(brief))
    assert code == 0 and be.calls == 2
    new = [p for p in (tmp_path / "runs").iterdir() if p.name not in before]
    assert len(new) == 1 and "-verify-" in new[0].name
    vdir = new[0]
    meta = json.loads((vdir / "run.json").read_text(encoding="utf-8"))
    assert meta["status"] == "finished" and meta["mode"] == "verify"
    assert meta["config"]["target"]["band_hi_hz"] == 12000.0
    assert meta["config"]["brief"]["name"] == "hifi_90x60_1in_12k"
    assert meta["verify_of"]["run"] == str(run_dir.resolve())
    rows = read_ndjson(vdir / "search.ndjson")
    assert len(rows) == 2 and all(r["mode"] == "verify" for r in rows)
    assert (vdir / "best.json").exists() and (vdir / "config.yaml").exists()
    assert not (run_dir / "verify").exists()                     # the source run is untouched
    assert cli.REPO not in vdir.parents


def test_verify_without_brief_keeps_writing_into_the_run(smoke_cfg, tmp_path, monkeypatch):
    run_dir, _ = _source_run(smoke_cfg, tmp_path, monkeypatch)
    code, be = _verify(tmp_path, monkeypatch, run_dir)
    assert code == 0 and be.calls == 2
    rows = read_ndjson(run_dir / "verify" / "search.ndjson")
    assert len(rows) == 2


def test_verify_only_briefs_are_refused_by_search_run_and_campaign(smoke_cfg, tmp_path, monkeypatch, capsys):
    """The 12 kHz briefs exceed what a search can mesh on 8 GB: only `verify --brief` may use them."""
    from hornlab_search.config import load_brief
    assert load_brief(BRIEF_12K)["verify_only"] is True
    common = ["--runs-dir", str(tmp_path / "runs"), "--dataset-dir", str(tmp_path / "ds"),
              "--cache-dir", str(tmp_path / "cache")]
    cfg_file = Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"
    (tmp_path / "runs").mkdir()
    assert cli.main(["search", "--config", str(cfg_file), "--brief", str(BRIEF_12K), *common]) == 2
    assert "verify_only" in capsys.readouterr().out
    assert list((tmp_path / "runs").glob("*-screen-*")) == []          # no empty run dir left behind
    assert cli.main(["run", "--config", str(cfg_file), "--brief", str(BRIEF_12K), *common]) == 2
    assert cli.main(["campaign", "--tier", "screen", "--families", "conical", "--brief", str(BRIEF_12K),
                     *common]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_verify_only_must_be_a_boolean(tmp_path):
    from hornlab_search.config import ConfigError, load_brief
    bad = tmp_path / "b.yaml"
    bad.write_text(BRIEF_12K.read_text(encoding="utf-8").replace("verify_only: true", "verify_only: yes please"),
                   encoding="utf-8")
    with pytest.raises(ConfigError, match="verify_only"):
        load_brief(bad)
