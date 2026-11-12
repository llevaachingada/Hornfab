"""``solve.julia_threads`` (CPU second lane, 2026-11-12): parse, validate, and keep it OUT of the
solve-spec hash. Offline: YAML only, no solver, no GPU."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config, solve_spec


def _load_doc(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_variant(tmp_path: Path, base_name: str, **solve_extra) -> Path:
    raw = _load_doc(EXAMPLES / base_name)
    raw.setdefault("solve", {})
    raw["solve"].update(solve_extra)
    path = tmp_path / f"{Path(base_name).stem}_variant.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_julia_threads_parses_as_a_positive_integer(tmp_path):
    cfg = load_config(_write_variant(tmp_path, "osse_baseline.yaml", julia_threads=12))
    assert cfg.solve.julia_threads == 12


def test_absent_julia_threads_is_none(tmp_path):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    assert cfg.solve.julia_threads is None


def test_two_configs_differing_only_in_julia_threads_share_every_solve_hash(tmp_path):
    flat = load_config(EXAMPLES / "osse_baseline.yaml")
    threaded = load_config(_write_variant(tmp_path, "osse_baseline.yaml", julia_threads=12))
    assert threaded.solve.julia_threads == 12 and flat.solve.julia_threads is None
    for mode in ("screen", "verify", "final"):
        assert solve_spec(mode, flat).hash() == solve_spec(mode, threaded).hash(), mode
        assert "julia_threads" not in dict(solve_spec(mode, threaded).extra)


@pytest.mark.parametrize("bad", [0, -1, True, 3.5, "12", 12.0])
def test_julia_threads_must_be_a_positive_integer(tmp_path, bad):
    with pytest.raises(ConfigError, match="julia_threads"):
        load_config(_write_variant(tmp_path, "osse_baseline.yaml", julia_threads=bad))


# ------------------------------------------------------------------ wiring (H9: one host, same key)


def test_the_thread_count_reaches_both_warm_and_solveconfig(monkeypatch):
    from hornlab_search.solve import beat as beat_mod
    seen: dict = {}
    monkeypatch.setattr(beat_mod.worker, "start_beat_worker",
                        lambda device, julia_threads=None:
                        seen.update(device=device, julia_threads=julia_threads))
    be = beat_mod.BeatBackend("cpu", julia_threads=7)
    be.warm()
    assert seen == {"device": "cpu", "julia_threads": 7}
    # SolveConfig gets the SAME number (a mismatch keys a second host, H9); absent sends nothing.
    assert beat_mod._julia_threads_kwargs(be.julia_threads) == {"julia_threads": 7}
    assert beat_mod._julia_threads_kwargs(None) == {}      # absent == library "auto"


def test_beat_backend_refuses_a_bad_thread_count():
    from hornlab_search.solve.beat import BeatBackend
    for bad in (0, -3, True):
        with pytest.raises(ValueError, match="julia_threads"):
            BeatBackend("cpu", julia_threads=bad)


def test_the_cli_backend_forwards_julia_threads(monkeypatch):
    from types import SimpleNamespace
    import hornlab_search.solve.base as base_mod
    from hornlab_search import cli
    seen: dict = {}
    monkeypatch.setattr(base_mod, "get_backend",
                        lambda name, **kw: seen.update({"name": name}, **kw) or object())
    cfg = SimpleNamespace(solve=SimpleNamespace(backend="beat_cpu", timeout_s=60.0,
                                                julia_threads=12))
    cli._backend(cfg)
    assert seen["name"] == "beat_cpu" and seen["julia_threads"] == 12
    seen.clear()
    cfg.solve.julia_threads = None
    cli._backend(cfg)
    assert "julia_threads" not in seen                     # absent stays the library "auto"
