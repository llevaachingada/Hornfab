"""Cloud hardening on top of the local issue-#13 set (2026-10-14): DI provenance guard, NaN refusal
in the unit-cube encoding, and an empty propose result failing loudly. Needs torch."""
import numpy as np
import pytest

pytest.importorskip("torch")

from test_surrogate_stage_a import EX, _synthetic  # noqa: E402

from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.surrogate.features import unit_matrix  # noqa: E402
from hornlab_search.surrogate.train import train_surrogate  # noqa: E402


@pytest.fixture(scope="module")
def setup():
    cfg = load_config(EX)
    return cfg, DesignSpace.from_config(cfg)


def test_unit_matrix_refuses_nan_instead_of_inventing_inputs(setup):
    _, space = setup
    arrays, _, _ = _synthetic(space, 10, 29)
    X = arrays["X"].copy()
    X[3, 1] = np.nan
    with pytest.raises(ValueError, match=f"'{space.keys()[1]}' is missing in 1 of 10"):
        unit_matrix(X, arrays["key_names"], space)


def test_train_refuses_cuts_estimate_di(setup):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 100, 19)
    ok = np.asarray(arrays["ok"], bool)
    src = np.where(ok, "balloon", "").astype("<U16")
    src[int(np.flatnonzero(ok)[0])] = "cuts_estimate"
    arrays["di_source"] = src
    with pytest.raises(ValueError, match="cuts_estimate"):
        train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=5)


@pytest.mark.timeout(600)
def test_propose_with_nothing_valid_fails(setup, tmp_path, capsys, monkeypatch):
    from hornlab_search.cli import main
    from hornlab_search.surrogate import ismo
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 300, 23)
    train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=30,
                    out_path=tmp_path / "s.pt")
    monkeypatch.setattr(ismo, "propose", lambda *a, **k: [])
    rc = main(["surrogate", "propose", "--config", str(EX), "--out", str(tmp_path / "s.pt"),
               "--proposals", str(tmp_path / "p.json"), "--allow-unvalidated"])
    assert rc == 1 and "0 designs" in capsys.readouterr().out
    assert not (tmp_path / "p.json").exists()
