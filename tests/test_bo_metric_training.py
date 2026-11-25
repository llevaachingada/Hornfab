"""Pass 1 metric-composite data layer: contribution extraction, selection, artifact.

Synthetic only (no solver, no dataset, no real archive).  The scorer parity tests call the
canonical ``objective_v10``/``objective_v11`` on tiny synthetic MetricSets/Responses, then prove
the extractor reproduces each contribution and the canonical total.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from hornlab_search.bo.metric_contracts import (
    NAN_TERM_FILL,
    MetricTrainingCandidate,
    SelectionPolicy,
    SelectionResult,
    component_names,
)
from hornlab_search.bo.metric_training import (
    bounds_identity,
    build_metric_training_artifact,
    extract_v10_contributions,
    extract_v11_contributions,
    select_metric_training_observations,
)
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.scalar_v10 import V10Params, objective_v10
from hornlab_search.objective.scalar_v11 import (
    CD_STATUS_CUTS_FALLBACK,
    CD_STATUS_UNMEASURABLE,
    V11Params,
    objective_v11,
)


# ---------------------------------------------------------------------------- synthetic scorer


ONES = {k: 1.0 for k in ("cov_profile", "rip", "flat", "load", "dislope", "di_roughness",
                         "flat_cv")}
V11_WEIGHTS = {"cov_profile": 1.0, "rip": 0.5, "flat": 0.5, "load": 1.0, "dislope": 0.5,
               "di_roughness": 0.5, "flat_cv": 0.5}
F = np.array([700.0, 1000.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0, 6300.0, 8000.0])
ANG = np.linspace(-90.0, 90.0, 73)
_T = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
      "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
      "f0_hz": 700.0}


def _row(hz, pref, lo=None, hi=None):
    out = {"hz": hz, "preferred_deg": pref}
    if lo is not None:
        out["min_deg"], out["max_deg"] = lo, hi
    return out


def _target():
    from hornlab_search.targets.spec import Target
    return Target.from_dict({**_T, "coverage_profile": {
        "mode": "corridor", "interpolation": "log_frequency",
        "h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
        "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}})


def _cd_block(**over):
    block = {
        "band_hz": [700.0, 8000.0],
        "window_h_deg": 30.0,
        "window_v_deg": 10.0,
        "lw": {"weight": 1.5, "tolerance_db": 1.5},
        "di_std": {"weight": 0.75, "tolerance_db": 1.0},
        "nacc": {"weight": 0.75, "tolerance": 0.02},
        "offaxis": {"weight": 1.0, "tolerance_db": 1.0, "reference": "band_mean",
                    "band_hz": [2500.0, 8000.0],
                    "angles_h_deg": [-40, -30, 30, 40],
                    "angles_v_deg": [-25, -10, 10, 25]},
        "report": {"omega": True, "contour": False},
    }
    block.update(over)
    return block


def _v10_params(**over):
    block = {"version": 10, "tolerances": dict(ONES), "ripple_region": "preferred_edge"}
    block.update(over)
    return V10Params.from_block(block)


def _v11_params(**cd_over):
    return V11Params.from_block({"version": 11, "tolerances": dict(ONES),
                                 "ripple_region": "preferred_edge",
                                 "cd": _cd_block(**cd_over)})


def _metrics(target):
    from hornlab_search.types import MetricSet
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


def _resp(balloon):
    from hornlab_search.types import Response
    n, na = F.size, ANG.size
    sh = np.full((n, na), 90.0)
    sv = np.full((n, na), 90.0)
    if balloon:
        dirs = _balloon_dirs()
        spl_bal = np.full((n, dirs.shape[0]), 90.0)
    else:
        dirs = None
        spl_bal = None
    return Response(
        freqs_hz=F.copy(), h_angles_deg=ANG.copy(), v_angles_deg=ANG.copy(),
        spl_h_db=sh, spl_v_db=sv, balloon_dirs=dirs, spl_balloon_db=spl_bal,
        z_throat=np.ones(n, dtype=complex), meta={})


def _v10_terms(**block_over):
    target, params = _target(), _v10_params(**block_over)
    j, terms = objective_v10(_metrics(target), _resp(True), True, target, None, params)
    return j, terms, params


def _v11_terms(balloon=True):
    target, params = _target(), _v11_params()
    j, terms = objective_v11(_metrics(target), _resp(balloon), True, target, V11_WEIGHTS, params)
    return j, terms, params


# ---------------------------------------------------------------------------- v10 extraction


def test_v10_extraction_reproduces_components_and_total():
    j, terms, params = _v10_terms()
    result = extract_v10_contributions(terms, params=params, observation_id="obs-v10")
    assert result.ok and result.status == "ok"
    assert result.objective_version == 10
    assert result.component_names == component_names(10)
    assert result.components is not None and result.components.shape == (4,)
    assert result.components.flags.writeable is False

    from hornlab_search.objective.scalar_v10 import resolve_v10_weights
    w = resolve_v10_weights(None, params)
    expected = np.array([w["load"] * terms["load"],
                         w["cov_profile"] * terms["cov_profile"],
                         w["rip"] * terms["rip"],
                         w["flat"] * terms["flat"] + w["dislope"] * terms["dislope"]
                         + w["di_roughness"] * terms["di_roughness"]
                         + w["flat_cv"] * terms["flat_cv"]])
    assert np.allclose(result.components, expected, rtol=0.0, atol=1e-12)
    assert result.j == pytest.approx(j, abs=1e-12)
    assert float(np.sum(result.components)) == pytest.approx(j, abs=1e-12)
    assert result.parity_abs <= result.parity_tol


def test_v10_optional_hf_floor_enters_other_j():
    _, base_terms, base_params = _v10_terms()
    base = extract_v10_contributions(base_terms, params=base_params)
    import copy
    hf_terms = copy.deepcopy(base_terms)
    # A valid term row for a brief that declares hf_floor carries the extra key; emulate it.
    hf_terms["hf_floor"] = 1.0                    # raw 2.0 / tolerance 2.0
    hf_terms["total"] = float(base_terms["total"]) + 0.5 * 1.0
    hf_params = _v10_params(hf_floor={"hz": 8000.0, "h_deg": 90.0, "v_deg": 60.0,
                                      "weight": 0.5, "tolerance": 2.0})
    result = extract_v10_contributions(hf_terms, params=hf_params)
    assert result.ok
    assert result.components[3] == pytest.approx(float(base.components[3]) + 0.5, abs=1e-12)
    assert "hf_floor" in hf_params.weighted_keys()


def test_v10_missing_and_unmeasurable_terms_are_refused():
    _, terms, params = _v10_terms()
    broken = dict(terms)
    broken.pop("flat")
    assert extract_v10_contributions(broken, params=params).reason == "missing_term:flat"

    nan = dict(terms)
    nan["load"] = NAN_TERM_FILL
    assert extract_v10_contributions(nan, params=params).reason == "unmeasurable_term:load"

    penalty = dict(terms)
    penalty["penalty"] = 1000.0
    assert extract_v10_contributions(penalty, params=params).reason == "penalty_row"

    parity = dict(terms)
    parity["total"] = float(terms["total"]) + 1.0
    assert extract_v10_contributions(parity, params=params).reason == "parity_mismatch"


def test_v10_cuts_estimate_di_policy():
    _, terms, params = _v10_terms()
    flagged = dict(terms)
    flagged["di_estimated"] = True
    refused = extract_v10_contributions(flagged, params=params)
    assert refused.reason == "cuts_estimate_di"
    allowed = extract_v10_contributions(
        flagged, params=params, policy=SelectionPolicy(allow_cuts_estimate_di=True))
    assert allowed.ok and "cuts_estimate_di" in allowed.quality_flags


# ---------------------------------------------------------------------------- v11 extraction


def test_v11_extraction_reproduces_components_and_total():
    j, terms, params = _v11_terms(balloon=True)
    result = extract_v11_contributions(terms, weights=V11_WEIGHTS, params=params,
                                       observation_id="obs-v11")
    assert result.ok and result.status == "ok"
    assert result.objective_version == 11
    assert result.component_names == component_names(11)
    assert result.components.shape == (6,)
    assert result.cd_status == "balloon"

    from hornlab_search.objective.scalar_v11 import resolve_v11_weights
    w = resolve_v11_weights(V11_WEIGHTS, params)
    active = params.v10.v9.weighted_keys()
    expected = np.array([
        w["load"] * terms["load"],
        sum(w[k] * terms[k] for k in active if k != "load"),
        w["cd_lw"] * terms["cd_lw"],
        w["cd_di_std"] * terms["cd_di_std"],
        w["cd_nacc"] * terms["cd_nacc"],
        w["offaxis_smooth"] * terms["offaxis_smooth"],
    ])
    assert np.allclose(result.components, expected, rtol=0.0, atol=1e-12)
    assert result.j == pytest.approx(j, abs=1e-12)
    assert float(np.sum(result.components)) == pytest.approx(j, abs=1e-12)


def test_v11_cuts_fallback_policy_and_unmeasurable_cd():
    _, cut_terms, params = _v11_terms(balloon=False)
    assert cut_terms["cd_status_code"] == CD_STATUS_CUTS_FALLBACK
    refused = extract_v11_contributions(cut_terms, weights=V11_WEIGHTS, params=params)
    assert refused.reason == "cd_cuts_fallback"
    allowed = extract_v11_contributions(
        cut_terms, weights=V11_WEIGHTS, params=params,
        policy=SelectionPolicy(allow_cd_cuts_fallback=True))
    assert allowed.ok and allowed.cd_status == "cuts_fallback"
    assert "cd_cuts_fallback" in allowed.quality_flags

    _, balloon_terms, _ = _v11_terms(balloon=True)
    unmeasurable = dict(balloon_terms)
    unmeasurable["cd_status_code"] = CD_STATUS_UNMEASURABLE
    assert (extract_v11_contributions(unmeasurable, weights=V11_WEIGHTS, params=params).reason
            == "cd_unmeasurable")


def test_v11_missing_component_term_is_refused():
    _, terms, params = _v11_terms(balloon=True)
    broken = dict(terms)
    broken.pop("cd_nacc")
    assert (extract_v11_contributions(broken, weights=V11_WEIGHTS, params=params).reason
            == "missing_term:cd_nacc")


# ---------------------------------------------------------------------------- selector


class _Encoding:
    version = "test-active-projection-v1"

    def __init__(self, d=3):
        self.d = d
        self.active_keys = tuple(f"k{i}" for i in range(d))

    def key_transforms(self):
        return {k: {"lo": 0.0, "hi": 1.0, "log": False, "transform": "identity",
                    "active": True} for k in self.active_keys}


ENC = _Encoding(3)
BOUNDS = bounds_identity(ENC)
IDENTITY = {
    "brief_hash": "brief-1",
    "score_hash": "score-1",
    "task_identity": "task-1",
    "backend": "beat_cuda",
    "fidelity": "screen",
    "grid_hash": "grid-1",
    "dependency_hash": "dep-1",
    "mesh_hash": "mesh-1",
}


def _x_for(i):
    return np.array([(0.37 * i) % 1.0, (0.61 * i) % 1.0, (0.83 * i) % 1.0], dtype=float)


def _cand(i, *, J=None, x=None, objective_version=10, **over):
    data = dict(
        observation_id=f"obs-{i:04d}",
        x=_x_for(i) if x is None else np.asarray(x, dtype=float),
        J=float(i) if J is None else float(J),
        objective_version=int(objective_version),
        physical_id=f"phys-{i:04d}",
        design_hash=f"design-{i:04d}",
        active_keys=ENC.active_keys,
        bounds_hash=BOUNDS,
        status="ok",
        **IDENTITY,
    )
    data.update(over)
    return MetricTrainingCandidate(**data)


def _select(records, **policy_over):
    return select_metric_training_observations(
        records, encoding=ENC, policy=SelectionPolicy(**policy_over))


def _reasons(selection):
    return {entry["observation_id"]: list(entry["reasons"]) for entry in selection.excluded}


def test_selector_includes_best_observation_at_index_299():
    records = [_cand(i, J=1.0 + 0.001 * i) for i in range(299)]
    records.append(_cand(299, J=-100.0))
    selection = _select(records)
    assert selection.ok and selection.n_selected == 256
    assert selection.n_available == 300 and selection.n_compatible == 300
    assert selection.n_unique == 300
    assert "obs-0299" in selection.selected_ids
    assert "obs-0299" not in selection.excluded_ids
    # 44 compatible observations fall outside the 256 cap and are recorded, never dropped.
    assert len(selection.excluded_ids) == 44


def test_selector_refuses_changed_identity_and_invalid_rows():
    records = [_cand(i) for i in range(20)]
    records += [
        _cand(100, objective_version=11),
        _cand(101, backend="cpu"),
        _cand(102, grid_hash="grid-2"),
        _cand(103, fidelity="verify"),
        _cand(104, bounds_hash="stale-bounds"),
        _cand(105, x=np.zeros(2)),
        _cand(106, status="solve_failed"),
    ]
    selection = _select(records)
    assert selection.ok and selection.n_unique == 20
    reasons = _reasons(selection)
    assert reasons["obs-0100"] == ["identity_mismatch:objective_version"]
    assert reasons["obs-0101"] == ["identity_mismatch:backend"]
    assert reasons["obs-0102"] == ["identity_mismatch:grid_hash"]
    assert reasons["obs-0103"] == ["identity_mismatch:fidelity"]
    assert reasons["obs-0104"] == ["bounds_identity_mismatch"]
    assert reasons["obs-0105"][0].startswith("x_shape")
    assert reasons["obs-0106"] == ["failed_solve:solve_failed"]


def test_selector_refuses_empty_required_identity_fields():
    records = [_cand(i) for i in range(16)]
    records.append(_cand(50, brief_hash=""))
    selection = _select(records)
    assert selection.ok and selection.n_selected == 16
    reasons = _reasons(selection)
    assert reasons["obs-0050"] == ["capability_missing:missing_identity:brief_hash"]


def test_selector_deduplicates_cached_and_refuses_conflicting_duplicates():
    records = [_cand(i) for i in range(16)]
    cached_a = _cand(100, physical_id="same-solve", J=1.0, x=np.full(3, 0.4))
    cached_b = _cand(101, physical_id="same-solve", J=1.0, x=np.full(3, 0.4))
    conflict_a = _cand(102, physical_id="conflict", J=2.0)
    conflict_b = _cand(103, physical_id="conflict", J=3.0)
    selection = _select(records + [cached_a, cached_b, conflict_a, conflict_b])
    assert selection.ok
    assert selection.n_unique == 17
    reasons = _reasons(selection)
    assert reasons["obs-0101"] == ["duplicate_cached"]
    assert reasons["obs-0102"] == ["duplicate_conflict"]
    assert reasons["obs-0103"] == ["duplicate_conflict"]
    assert "obs-0100" in selection.selected_ids


def test_selector_x_is_round_tripped_exactly_and_never_clipped():
    rng = np.random.default_rng(4)
    xs = [rng.random(3) for _ in range(16)]
    records = [_cand(i, x=xs[i]) for i in range(16)]
    records.append(_cand(90, x=np.array([1.2, 0.5, 0.5])))
    selection = _select(records)
    assert selection.ok
    reasons = _reasons(selection)
    assert reasons["obs-0090"] == ["x_out_of_box"]
    by_id = {c.observation_id: c for c in selection.selected}
    for i in range(16):
        assert np.array_equal(by_id[f"obs-{i:04d}"].x, xs[i])


def test_selector_below_n_min_is_needs_initial_data_but_publishes_lowest_j():
    records = [_cand(0, J=3.0), _cand(1, J=1.0), _cand(2, J=2.0)]
    selection = _select(records, n_max=2)
    assert selection.status == "needs_initial_data"
    assert selection.n_unique == 3 and selection.n_selected == 2
    assert selection.selected_ids == ("obs-0001", "obs-0002")
    assert _reasons(selection)["obs-0000"] == ["not_selected:n_max_cap"]


# ---------------------------------------------------------------------------- artifact


def _component_cohort(n=16):
    names = component_names(10)
    records = []
    for i in range(n):
        components = np.array([float(i), 0.0, 0.0, 0.0])
        records.append(_cand(i, J=float(i), components=components, component_names=names))
    return records


def test_artifact_checksum_is_deterministic_and_arrays_are_immutable():
    selection = _select(_component_cohort(16))
    assert selection.ok
    identity = {"brief_hash": "brief-1", "score_hash": "score-1", "backend": "beat_cuda"}
    first = build_metric_training_artifact(selection, identity_metadata=identity)
    second = build_metric_training_artifact(selection, identity_metadata=identity)
    assert first.ok and second.ok
    assert first.checksum == second.checksum
    assert first.X.flags.writeable is False
    assert first.J.flags.writeable is False
    assert first.Y_components.flags.writeable is False
    assert first.X.dtype == np.float64 and first.J.shape == (16, 1)
    assert first.Y_components.shape == (16, 4)
    assert np.allclose(np.sum(first.Y_components, axis=1), first.J[:, 0], atol=1e-12)
    assert first.metadata["manifest_checksum"] == first.checksum

    original = first.X.tobytes()
    selection.selected[0].x[0] = 0.123456
    assert first.X.tobytes() == original


def test_artifact_refuses_missing_components():
    selection = _select(_component_cohort(16))
    assert selection.ok
    broken = dataclasses.replace(selection.selected[0], components=None, component_names=())
    selection = dataclasses.replace(selection, selected=(broken,) + selection.selected[1:])
    artifact = build_metric_training_artifact(selection, identity_metadata={})
    assert artifact.status == "refused"
    assert any("has no components" in reason for reason in artifact.reasons)
