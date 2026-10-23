"""surrogate train/propose/round refuse typology generator configs with a clear message. Offline."""
from __future__ import annotations

from pathlib import Path

import pytest

from hornlab_search.config import load_config
from hornlab_search.surrogate.features import UnsupportedConfigError, require_surrogate_config

ROOT = Path(__file__).resolve().parents[1]


def test_generator_config_is_refused_with_a_clear_message():
    cfg = load_config(ROOT / "examples" / "typologies" / "osse_axi.yaml")
    with pytest.raises(UnsupportedConfigError, match="does not support typology generator configs"):
        require_surrogate_config(cfg)


def test_native_config_is_accepted():
    require_surrogate_config(load_config(ROOT / "examples" / "osse_baseline.yaml"))


def test_cli_surrogate_train_refuses_generator_config(capsys):
    pytest.importorskip("torch")
    from hornlab_search import cli
    rc = cli.main(["surrogate", "train", "--config",
                   str(ROOT / "examples" / "typologies" / "osse_axi.yaml"), "--out", "unused"])
    assert rc == 1
    assert "does not support typology generator configs" in capsys.readouterr().out
