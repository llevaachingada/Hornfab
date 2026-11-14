"""``solve.freq_batch_size`` (C3, speed program E8): parse, validate, and prove it is provenanced
in ``config_sha`` while its absence leaves every existing hash untouched.

Offline: YAML only, no solver, no GPU.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config
from hornlab_search.search.rundir import config_sha

BASE = "osse_baseline.yaml"


def _load_doc(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_variant(tmp_path: Path, **solve_extra) -> Path:
    raw = _load_doc(EXAMPLES / BASE)
    raw.setdefault("solve", {})
    raw["solve"].update(solve_extra)
    path = tmp_path / f"{Path(BASE).stem}_variant.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_absent_freq_batch_size_is_none():
    cfg = load_config(EXAMPLES / BASE)
    assert cfg.solve.freq_batch_size is None


def test_freq_batch_size_12_is_accepted(tmp_path):
    cfg = load_config(_write_variant(tmp_path, freq_batch_size=12))
    assert cfg.solve.freq_batch_size == 12


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "12"])
def test_freq_batch_size_must_be_a_positive_integer(tmp_path, bad):
    with pytest.raises(ConfigError, match="freq_batch_size"):
        load_config(_write_variant(tmp_path, freq_batch_size=bad))


def test_freq_batch_size_is_refused_for_bempp_cpu(tmp_path):
    with pytest.raises(ConfigError, match="bempp_cpu"):
        load_config(_write_variant(tmp_path, backend="bempp_cpu", freq_batch_size=12))


def test_the_key_is_provenanced_in_config_sha(tmp_path):
    flat = load_config(EXAMPLES / BASE)
    batched = load_config(_write_variant(tmp_path, freq_batch_size=12))
    assert flat.raw["solve"].get("freq_batch_size") is None
    assert batched.raw["solve"]["freq_batch_size"] == 12
    assert config_sha(batched.raw) != config_sha(flat.raw)


def test_the_field_addition_alone_does_not_change_the_hash_of_a_config_without_the_key():
    cfg = load_config(EXAMPLES / BASE)
    # The dataclass default is never injected into raw: a config that does not name the key hashes
    # exactly as the raw YAML on disk does (the pre-field-addition hash).
    assert "freq_batch_size" not in cfg.raw.get("solve", {})
    assert config_sha(cfg.raw) == config_sha(_load_doc(EXAMPLES / BASE))
