"""Focused tests for hornlab_search/bo/encoding.py (B2 M0, offline; no mesh/BEM)."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.bo import (
    ActiveProjection,
    EncodingError,
    HashMismatchError,
    HistoricalClippingError,
    MissingKeyError,
    UnsupportedSpaceError,
)
from hornlab_search.config import load_config
from hornlab_search.design.space import Bound, DesignSpace
from hornlab_search.types import Design

CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_config(CONFIG)


@pytest.fixture(scope="module")
def space(cfg):
    return DesignSpace.from_config(cfg)


@pytest.fixture(scope="module")
def projected(space):
    return ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})


def test_full_order_is_alphabetical_and_identity_projection(space):
    enc = ActiveProjection.identity(space)
    assert enc.full_keys == tuple(space.keys())
    assert enc.full_keys == tuple(sorted(enc.full_keys))
    assert enc.full_d == enc.d == 14
    assert enc.fixed_values == {}
    assert enc.to_active(np.arange(14) / 14.0).shape == (14,)


def test_projection_removes_only_the_declared_noop(projected, space):
    assert projected.full_d == 14
    assert projected.d == 13
    assert "morph_exponent" not in projected.active_keys
    assert projected.fixed_values == {"morph_exponent": 4.0}
    # The full alphabetical vector is reconstructed before space.denormalize.
    active = np.full(projected.d, 0.25)
    full = projected.to_full(active)
    assert full.shape == (14,)
    idx = projected.full_keys.index("morph_exponent")
    expected_u, clipped = space.bounds["morph_exponent"].to_unit(4.0)
    assert clipped is False
    assert full[idx] == pytest.approx(expected_u)
    assert projected.to_active(full) == pytest.approx(active)


def test_round_trip_seed_is_hash_exact(projected, space):
    x = projected.normalize_design(space.seed)
    assert x.shape == (13,)
    rt = projected.denormalize(x)
    assert rt.hash() == space.seed.hash()
    # A decoded full vector keeps the fixed reference value.
    assert rt.params["morph_exponent"] == pytest.approx(4.0)


def test_missing_key_refuses(projected, space):
    params = dict(space.seed.params)
    params.pop("L_mm")
    with pytest.raises(MissingKeyError):
        projected.normalize_design(Design("OSSE", params))


def test_historical_clipping_refuses(projected, space):
    params = dict(space.seed.params)
    params["L_mm"] = 9999.0  # outside resolved bounds.L_mm [104, 520]
    with pytest.raises(HistoricalClippingError):
        projected.normalize_design(Design("OSSE", params))


def test_hash_mismatched_round_trip_refuses(projected, space):
    # exponent is fixed by search:false; denormalize copies the seed value, so the
    # observation is not representable and must be rejected rather than silently changed.
    params = dict(space.seed.params)
    params["exponent"] = 3.0
    with pytest.raises(HashMismatchError):
        projected.normalize_design(Design("OSSE", params))


def test_unsupported_discrete_active_dimension_refuses(space):
    disc = DesignSpace(
        family="OSSE",
        seed=space.seed,
        bounds={"morph_target": Bound(lo=0.0, hi=3.0, search=True)},
    )
    with pytest.raises(UnsupportedSpaceError):
        ActiveProjection.from_space(disc)


def test_log_bound_transform_round_trips(space):
    log_space = DesignSpace(
        family="OSSE",
        seed=space.seed,
        bounds={"L_mm": Bound(lo=100.0, hi=1000.0, search=True, log=True)},
    )
    enc = ActiveProjection.from_space(log_space)
    assert enc.key_transforms()["L_mm"]["log"] is True
    assert enc.key_transforms()["L_mm"]["transform"] == "log10"
    x = enc.normalize_design(log_space.seed)
    # 260 mm on a [100, 1000] log10 box.
    assert x[0] == pytest.approx((np.log10(260.0) - 2.0) / 1.0)
    rt = enc.denormalize(x)
    assert rt.params["L_mm"] == pytest.approx(260.0, abs=1e-9)
    assert rt.hash() == log_space.seed.hash()


def test_decode_out_of_box_refuses_unless_explicitly_clipped(projected):
    bad = np.full(projected.d, 0.5)
    bad[0] = 1.5
    with pytest.raises(HistoricalClippingError):
        projected.denormalize(bad)
    d = projected.denormalize(bad, clip=True)
    assert isinstance(d, Design)


def test_noop_key_must_exist(space):
    with pytest.raises(UnsupportedSpaceError):
        ActiveProjection.from_space(space, no_ops={"not_a_key": 1.0})
