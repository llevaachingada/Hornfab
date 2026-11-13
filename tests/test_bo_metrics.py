"""Focused tests for the canonical v4 raw metric policy (B2 M2/M3 seam).

These tests are pure numpy + the resolved-brief loader.  They never solve, mesh, import
bo/model, or call a backend.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.bo.metrics import (
    RIPPLE_LEGACY,
    RIPPLE_RESPONSE_DETRENDED,
    assert_ripple_response_detrended,
    make_legacy_ripple_policy,
    resolve_metric_policy,
)

BRIEF = REPO / "examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml"

#: 400..7000 Hz are inside the frozen 300-8000 Hz band; 9000 Hz is outside.
FREQS = (400.0, 800.0, 1280.0, 2000.0, 3000.0, 5000.0, 7000.0, 9000.0)


@pytest.fixture(scope="module")
def policy():
    return resolve_metric_policy(BRIEF, FREQS)


# ------------------------------------------------------------------ resolved brief


def test_policy_resolves_frozen_v4_ratio_and_support(policy):
    assert policy.objective_version == 4
    assert policy.cov_narrow_ratio == 2.0          # never V8Params.for_class("A") == 1.0
    assert policy.cov_below_f0 == "mask"
    assert policy.diag_reference == "round"
    assert policy.ripple == RIPPLE_RESPONSE_DETRENDED
    assert policy.status == "complete" and not policy.partial
    assert policy.weights == {
        "cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
        "load": 0.0, "distd": 0.5, "diag": 0.5,
    }
    assert policy.tolerances["cov"] == 2.0 and policy.tolerances["rip"] == 1.0
    assert policy.tolerances["diag"] == 2.0
    assert policy.freq_weights_signature == ((2500.0, 5500.0, 2.0),)
    assert "resolved_from_brief" in policy.reasons
    assert "load_weight_zero_no_impedance_claim" in policy.reasons
    # Band ends inclusive, f0 masks coverage below 1280 Hz, freq weight x2 in 2.5-5.5 kHz.
    assert policy.masks["ripple"] == (True, True, True, True, True, True, True, False)
    assert policy.masks["coverage_h"] == (False, False, True, True, True, True, True, False)
    assert policy.masks["coverage_v"] == policy.masks["coverage_h"]
    assert policy.frequency_weights == (1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0)
    assert len(policy.metric_spec_hash) == 64


def test_policy_without_frequencies_freezes_brief_identity_only():
    p = resolve_metric_policy(BRIEF)
    assert p.cov_narrow_ratio == 2.0
    assert p.masks is None and p.frequency_hz is None and p.frequency_weights is None
    assert p.status == "complete"
    assert len(p.metric_spec_hash) == 64


def test_policy_identity_is_deterministic(policy):
    again = resolve_metric_policy(BRIEF, FREQS)
    assert again.metric_spec_hash == policy.metric_spec_hash
    assert again.as_dict() == policy.as_dict()


# ------------------------------------------------------------------ ripple identity


def test_legacy_ripple_is_a_distinct_partial_metric(policy):
    legacy = make_legacy_ripple_policy(BRIEF, freqs_hz=FREQS)
    assert legacy.ripple == RIPPLE_LEGACY != policy.ripple
    assert legacy.status == "partial" and legacy.partial
    assert legacy.metric_spec_hash != policy.metric_spec_hash
    assert "legacy_ripple_fallback" in legacy.reasons
    # The no-argument factory still returns a named, partial, distinct identity.
    bare = make_legacy_ripple_policy()
    assert bare.ripple == RIPPLE_LEGACY and bare.status == "partial"
    assert bare.metric_spec_hash != legacy.metric_spec_hash


def test_assert_ripple_response_detrended_accepts_only_strict_support(policy):
    mask = np.asarray(policy.masks["ripple"], dtype=bool)
    assert assert_ripple_response_detrended(True, mask) is True
    with pytest.raises(ValueError, match="ripple_legacy_fallback"):
        assert_ripple_response_detrended(False, mask)
    with pytest.raises(ValueError, match="ripple_legacy_fallback"):
        assert_ripple_response_detrended(None, mask)
    with pytest.raises(ValueError, match="no_scored_support"):
        assert_ripple_response_detrended(True, np.zeros(mask.size, dtype=bool))
    with pytest.raises(ValueError, match="no_scored_support"):
        assert_ripple_response_detrended(True, None)


# ------------------------------------------------------------------ malformed declarations


def _declared(policy):
    return {name: np.asarray(mask, dtype=bool) for name, mask in policy.masks.items()}


def test_declared_masks_identical_to_target_are_complete(policy):
    p = resolve_metric_policy(BRIEF, FREQS, declared_masks=_declared(policy))
    assert p.status == "complete"
    assert p.metric_spec_hash == policy.metric_spec_hash
    assert p.masks == policy.masks


def test_declared_missing_bin_is_refused(policy):
    masks = _declared(policy)
    masks["coverage_h"] = masks["coverage_h"].copy()
    masks["coverage_h"][3] = False  # a bin the target requires is dropped
    with pytest.raises(ValueError, match="unexpected_missing_bins"):
        resolve_metric_policy(BRIEF, FREQS, declared_masks=masks)


def test_declared_unequal_support_is_refused(policy):
    masks = _declared(policy)
    masks["coverage_v"] = np.ones(len(FREQS) - 1, dtype=bool)
    with pytest.raises(ValueError, match="unequal_support"):
        resolve_metric_policy(BRIEF, FREQS, declared_masks=masks)
    with pytest.raises(ValueError, match="unequal_support"):
        resolve_metric_policy(BRIEF, FREQS, declared_weights=np.ones(len(FREQS) - 1))


def test_declared_no_scored_mask_is_refused(policy):
    masks = _declared(policy)
    masks["coverage_h"] = np.zeros(len(FREQS), dtype=bool)
    with pytest.raises(ValueError, match="no_scored_mask"):
        resolve_metric_policy(BRIEF, FREQS, declared_masks=masks)
    with pytest.raises(ValueError, match="no_scored_mask"):
        resolve_metric_policy(BRIEF, FREQS, declared_masks={"ripple": masks["ripple"]})


def test_invalid_or_zero_total_weights_are_refused(policy):
    with pytest.raises(ValueError, match="invalid_weights"):
        resolve_metric_policy(BRIEF, FREQS, declared_weights=-np.ones(len(FREQS)))
    bad = np.ones(len(FREQS))
    bad[2] = np.nan
    with pytest.raises(ValueError, match="invalid_weights"):
        resolve_metric_policy(BRIEF, FREQS, declared_weights=bad)
    zero = np.ones(len(FREQS))
    zero[np.asarray(policy.masks["coverage_h"], dtype=bool)] = 0.0
    with pytest.raises(ValueError, match="zero_total_weight"):
        resolve_metric_policy(BRIEF, FREQS, declared_weights=zero)


def test_shared_restricted_mask_is_a_distinct_partial_identity(policy):
    restriction = np.ones(len(FREQS), dtype=bool)
    restriction[6] = False  # drop 7000 Hz for every compared design
    p = resolve_metric_policy(BRIEF, FREQS, restricted_mask=restriction,
                              restriction_name="shared-7000")
    assert p.status == "partial"
    assert p.restriction_name == "shared-7000"
    assert p.masks["coverage_h"] == (False, False, True, True, True, True, False, False)
    assert p.metric_spec_hash != policy.metric_spec_hash
    assert "predeclared_restricted_mask:shared-7000" in p.reasons

    # The same declared restricted mask is reproducible (one shared metric identity).
    p2 = resolve_metric_policy(BRIEF, FREQS, restricted_mask=restriction,
                               restriction_name="shared-7000")
    assert p2.metric_spec_hash == p.metric_spec_hash
    # The identity is content-addressed by the mask, not by its declaration label.
    renamed = resolve_metric_policy(BRIEF, FREQS, restricted_mask=restriction,
                                    restriction_name="another-label")
    assert renamed.metric_spec_hash == p.metric_spec_hash

    declared = {k: np.asarray(policy.masks[k], dtype=bool) & restriction
                for k in policy.masks}
    p3 = resolve_metric_policy(BRIEF, FREQS, declared_masks=declared,
                               restricted_mask=restriction, restriction_name="shared-7000")
    assert p3.status == "partial" and p3.metric_spec_hash == p.metric_spec_hash

    for bad in (np.ones(len(FREQS), dtype=bool), np.zeros(len(FREQS), dtype=bool)):
        with pytest.raises(ValueError, match="invalid_restricted_mask"):
            resolve_metric_policy(BRIEF, FREQS, restricted_mask=bad,
                                  restriction_name="all-or-nothing")
