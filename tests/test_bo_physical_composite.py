"""Focused tests for the research-only physical-metric composite module.

Synthetic only: no BEM/GPU/mesh/solver, no real data.  Formula parity is checked against the
canonical ``objective_v11`` scorer on a tiny synthetic side-symmetric response, and against the
raw ``metrics.cd.cd_metrics`` payload it consumed.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hornlab_search.metrics.cd import cd_metrics
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.scalar_v11 import V11Params, objective_v11
from hornlab_search.bo.physical_composite import (
    PHYSICAL_METRIC_SPECS,
    PHYSICAL_SCHEMA_HASH,
    PHYSICAL_TERM_KEYS,
    POLICY_LABEL,
    RESEARCH_POLICY,
    fit_physical_model,
    evaluate_physical_transform,
    extract_physical_contributions,
    reconstruct_physical_j,
)
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet, Response

from hornlab_search.bo.policy import PROPOSAL_POLICIES

ONES = {k: 1.0 for k in ("cov_profile", "rip", "flat", "load", "dislope", "di_roughness",
                         "flat_cv")}
F = np.array([700.0, 1000.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0, 6300.0, 8000.0])
ANG = np.linspace(-90.0, 90.0, 73)


def _row(hz, pref, lo=None, hi=None):
    out = {"hz": hz, "preferred_deg": pref}
    if lo is not None:
        out["min_deg"], out["max_deg"] = lo, hi
    return out


def _target() -> Target:
    return Target.from_dict({
        "coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
        "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
        "f0_hz": 700.0,
        "coverage_profile": {
            "mode": "corridor", "interpolation": "log_frequency",
            "h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
            "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}})


def _params() -> V11Params:
    return V11Params.from_block({
        "version": 11, "tolerances": dict(ONES), "ripple_region": "preferred_edge",
        "cd": {
            "band_hz": [700.0, 8000.0], "window_h_deg": 30.0, "window_v_deg": 10.0,
            "lw": {"weight": 1.5, "tolerance_db": 1.5},
            "di_std": {"weight": 0.75, "tolerance_db": 1.0},
            "nacc": {"weight": 0.75, "tolerance": 0.02},
            "offaxis": {"weight": 1.0, "tolerance_db": 1.0, "reference": "band_mean",
                        "band_hz": [2500.0, 8000.0],
                        "angles_h_deg": [-40, -30, 30, 40],
                        "angles_v_deg": [-25, -10, 10, 25]},
            "report": {"omega": True, "contour": False}}})


def _metrics(target: Target) -> MetricSet:
    ref = target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg)
    n = F.size
    return MetricSet(
        freqs_hz=F.copy(), bw_h_deg=np.full(n, 80.0), bw_v_deg=np.full(n, 50.0),
        di_db=np.full(n, ref), di_source="balloon",
        ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n),
        z_throat_real=np.ones(n), scalars={})


def _balloon_dirs(n_theta=13, n_phi=24):
    dirs = []
    for th in np.linspace(0.0, 180.0, n_theta):
        st, ct = math.sin(math.radians(th)), math.cos(math.radians(th))
        for ph in np.linspace(0.0, 360.0, n_phi, endpoint=False):
            dirs.append([st * math.cos(math.radians(ph)), st * math.sin(math.radians(ph)), ct])
    return np.asarray(dirs, dtype=float)


def _resp(balloon: bool) -> Response:
    n, na = F.size, ANG.size
    sh = np.full((n, na), 90.0)
    sv = np.full((n, na), 90.0)
    if balloon:
        dirs = _balloon_dirs()
        bal = np.full((n, dirs.shape[0]), 90.0)
    else:
        dirs, bal = None, None
    return Response(freqs_hz=F.copy(), h_angles_deg=ANG.copy(), v_angles_deg=ANG.copy(),
                    spl_h_db=sh, spl_v_db=sv, balloon_dirs=dirs, spl_balloon_db=bal,
                    z_throat=np.ones(n, dtype=complex), meta={})


def _synthetic_v11():
    target, params = _target(), _params()
    metrics = _metrics(target)
    resp = _resp(True)
    j, terms = objective_v11(metrics, resp, True, target, None, params)
    cd = params.cd
    raw = cd_metrics(metrics, resp, cd.band_hz, cd.window_h_deg, cd.window_v_deg,
                     cd.offaxis["band_hz"], cd.offaxis["angles_h_deg"],
                     cd.offaxis["angles_v_deg"], cd.offaxis["reference"])
    return j, terms, params, raw


# ------------------------------------------------------------------ specs and units


def test_metric_specs_are_v11_only_physical_and_stable():
    assert [s.metric_key for s in PHYSICAL_METRIC_SPECS] == [
        "cd_lw_db", "cd_di_std_db", "cd_nacc", "offaxis_smooth_db"]
    assert [s.units for s in PHYSICAL_METRIC_SPECS] == ["dB", "dB", "ratio", "dB"]
    assert all(s.objective_version == 11 for s in PHYSICAL_METRIC_SPECS)
    assert all(s.missing_policy == "refuse" for s in PHYSICAL_METRIC_SPECS)
    for spec in PHYSICAL_METRIC_SPECS:
        assert len(spec.identity_hash) == 64
        assert spec.identity_hash == spec.identity_hash
    assert len(PHYSICAL_SCHEMA_HASH) == 64
    assert POLICY_LABEL and "research" in POLICY_LABEL.lower()


def test_physical_policy_is_not_registrable():
    assert RESEARCH_POLICY not in PROPOSAL_POLICIES
    assert "physical" not in " ".join(PROPOSAL_POLICIES)


# ------------------------------------------------------------------ extraction parity


def test_extraction_matches_canonical_v11_terms_and_hand_formula():
    from hornlab_search.objective.scalar_v11 import resolve_v11_weights

    j, terms, params, raw = _synthetic_v11()
    result = extract_physical_contributions(raw, params=params)
    assert result.ok and result.status == "ok"
    assert result.cd_status == "balloon" and result.cuts_fallback is False
    w = resolve_v11_weights(None, params)
    expected = np.array([
        w["cd_lw"] * terms["cd_lw"],
        w["cd_di_std"] * terms["cd_di_std"],
        w["cd_nacc"] * terms["cd_nacc"],
        w["offaxis_smooth"] * terms["offaxis_smooth"],
    ])
    np.testing.assert_allclose(result.contributions, expected, rtol=0.0, atol=1e-12)
    # Hand formula in physical units, using the tolerance block the caller supplied.
    hand = np.array([
        w["cd_lw"] * raw["cd_lw_db"] / params.cd.lw["tolerance_db"],
        w["cd_di_std"] * raw["cd_di_std_db"] / params.cd.di_std["tolerance_db"],
        w["cd_nacc"] * (1.0 - raw["cd_nacc"]) / params.cd.nacc["tolerance"],
        w["offaxis_smooth"] * raw["offaxis_smooth_db"] / params.cd.offaxis["tolerance_db"],
    ])
    np.testing.assert_allclose(result.contributions, hand, rtol=0.0, atol=1e-12)
    assert result.contributions_by_term.keys() == set(PHYSICAL_TERM_KEYS)
    # The four CD contributions alone do not reconstruct the canonical J.
    assert float(np.sum(result.contributions)) < float(j)


def test_missing_nonfinite_and_status_are_refusals_never_filled():
    _, _, params, raw = _synthetic_v11()
    missing = {k: v for k, v in raw.items() if k != "cd_lw_db"}
    assert extract_physical_contributions(missing, params=params).status == "unavailable"
    nan = dict(raw, cd_nacc=float("nan"))
    assert extract_physical_contributions(nan, params=params).status == "unavailable"
    unmeasurable = dict(raw, cd_status="unmeasurable")
    refused = extract_physical_contributions(unmeasurable, params=params)
    assert refused.status == "unavailable" and refused.reason == "cd_status_unavailable"
    out_of_range = dict(raw, cd_nacc=1.5)
    assert extract_physical_contributions(out_of_range, params=params).reason == (
        "cd_nacc_out_of_range")
    assert extract_physical_contributions(raw, params=None).reason == "params_required"
    assert extract_physical_contributions(raw, params=params, objective_version=10).reason == (
        "unsupported_objective_version")


def test_cuts_fallback_is_refused_by_default_and_flagged_when_allowed():
    target, params = _target(), _params()
    metrics = _metrics(target)
    resp = _resp(False)
    cd = params.cd
    raw = cd_metrics(metrics, resp, cd.band_hz, cd.window_h_deg, cd.window_v_deg,
                     cd.offaxis["band_hz"], cd.offaxis["angles_h_deg"],
                     cd.offaxis["angles_v_deg"], cd.offaxis["reference"])
    assert raw["cd_status"] == "cuts_fallback"
    refused = extract_physical_contributions(raw, params=params)
    assert refused.status == "unavailable" and "cuts_fallback" in refused.reason
    allowed = extract_physical_contributions(raw, params=params, allow_cd_cuts_fallback=True)
    assert allowed.ok and allowed.cuts_fallback is True
    assert "cd_cuts_fallback" in allowed.quality_flags


# ------------------------------------------------------------------ reconstruction


def test_cd_terms_alone_are_partial_and_name_the_missing_base_terms():
    _, _, params, raw = _synthetic_v11()
    cd = extract_physical_contributions(raw, params=params)
    partial = reconstruct_physical_j(cd_contributions=cd.contributions_by_term, params=params)
    assert partial.status == "partial" and partial.partial is True
    assert partial.j is None
    assert set(partial.missing_terms) == set(params.weighted_keys())
    assert set(PHYSICAL_TERM_KEYS).issubset(set(partial.supplied_terms))


def test_full_reconstruction_requires_every_base_contribution():
    from hornlab_search.objective.scalar_v11 import resolve_v11_weights

    j, terms, params, raw = _synthetic_v11()
    w = resolve_v11_weights(None, params)
    cd = extract_physical_contributions(raw, params=params)
    base = {k: float(w[k]) * float(terms[k]) for k in params.weighted_keys()}
    full = reconstruct_physical_j(base_contributions=base,
                                  cd_contributions=cd.contributions_by_term, params=params)
    assert full.ok and full.partial is False
    assert full.j == pytest.approx(float(j), abs=1e-12)
    assert full.missing_terms == ()
    # Dropping one base term makes it partial again.
    dropped = dict(base)
    dropped.pop(params.weighted_keys()[0])
    partial = reconstruct_physical_j(base_contributions=dropped,
                                     cd_contributions=cd.contributions_by_term, params=params)
    assert partial.partial is True and partial.j is None
    assert partial.missing_terms == (params.weighted_keys()[0],)
    # No params means the required base set is unknown: never claim a full J.
    no_params = reconstruct_physical_j(contributions={**base, **cd.contributions_by_term})
    assert no_params.partial is True and no_params.j is None


# ------------------------------------------------------------------ GP fit / samples


def _physical_data(n=20, d=2, seed=4):
    rng = np.random.default_rng(seed)
    X = rng.random((n, d))
    Y = np.column_stack([
        0.20 + 0.30 * X[:, 0],
        0.10 + 0.20 * X[:, 1] ** 2,
        1.0 - 0.05 * X[:, 0] - 0.02 * X[:, 1],
        0.10 + 0.15 * X[:, 0] * X[:, 1],
    ])
    return X, Y


@pytest.fixture(scope="module")
def physical_fit():
    X, Y = _physical_data()
    return X, Y, fit_physical_model(X, Y, seed=0, max_iters=30)


def test_physical_fit_is_research_only_and_tagged(physical_fit):
    X, Y, result = physical_fit
    assert result.status == "ok" and result.reason == "ok"
    assert result.research_only is True
    assert result.policy == RESEARCH_POLICY
    assert result.output_names == tuple(s.metric_key for s in PHYSICAL_METRIC_SPECS)
    assert result.d == 2 and result.n == 20
    assert result.model is not None
    assert np.array_equal(result.train_X, X)
    assert len(result.metric_specs) == 4
    assert len(result.per_output) == 4
    assert all(record["posterior_finite"] for record in result.per_output)


def test_nonlinear_transform_is_evaluated_on_samples(physical_fit):
    X, _, result = physical_fit
    query = np.linspace(0.05, 0.95, 7).reshape(-1, 1)
    query = np.concatenate([query, np.full_like(query, 0.5)], axis=1)
    # A quadratic transform: mean(transform(samples)) = mean^2 + var > transform(mean).
    transform = lambda samples: samples[..., 0] ** 2  # noqa: E731 - tiny test transform
    out = evaluate_physical_transform(result, query, transform, n_samples=256, seed=2)
    assert out.ok and out.sampled_mean is not None
    gap = np.asarray(out.sampled_mean) - np.asarray(out.transform_of_mean)
    assert float(np.max(np.abs(gap))) > 1e-6, (
        "sample transform must differ from transform-of-mean")
    assert not np.allclose(np.asarray(out.sampled_mean),
                           np.asarray(out.transform_of_mean), rtol=0.0, atol=1e-9)


def test_fit_refuses_nonfinite_and_bad_shapes():
    X, Y = _physical_data(n=10)
    bad = np.array(Y, copy=True)
    bad[0, 1] = np.nan
    assert fit_physical_model(X, bad).status == "unavailable"
    assert fit_physical_model(X, Y[:, :2]).reason == "output_fit_failed"
    assert fit_physical_model(X, Y, output_names=["nope_db"]).status == "unavailable"
    assert fit_physical_model(np.zeros((1, 2)), np.zeros((1, 4))).reason == "insufficient_data"
