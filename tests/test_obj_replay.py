"""Offline tests for the canonical replay adapter (R0).

Synthetic Response/MetricSet fixtures only: no mesh, no BEM, no GPU, no backend. The real ATH v4
brief is resolved through ``config.load_brief`` so the test exercises the production brief path.

Contracts pinned here:
* original v4 replay reproduces the stored J from the preserved raw response + metric arrays;
* a weights/tolerances change creates a new score identity with the same physical and metric ids;
* a supported target/band/coverage change regenerates target-dependent metrics from the response
  (new metric id, same physical id) and never reweights stored terms;
* a target change without response arrays refuses (``additional_data_or_solve_required``);
* missing balloon (weighted diag), impedance (weighted load), MEH/v5 inputs refuse or are labelled
  partial; incomplete rows never rank beside complete rows;
* identity hashes are deterministic.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from conftest import REPO, make_fake_response
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.objective import replay
from hornlab_search.objective.scalar_v4 import V4Params, objective_v4
from hornlab_search.solve.cache import save_response
from hornlab_search.targets.spec import Target

BRIEF_PATH = (REPO / "examples" / "briefs" / "campaign_2026-10-26_v4"
              / "native_ath_core_2in_v4.yaml")
TYPOLOGY = (REPO / "examples" / "typologies" / "campaign_2026-10-26_v4"
            / "native__ath_core_v4.yaml")


@pytest.fixture(scope="module")
def brief():
    return replay.load_brief_context(BRIEF_PATH)


def _record(brief, *, response=None, target=None, weights=None, block=None):
    """Build (meta, arrays) for a synthetic evaluation scored with the canonical v4 objective."""
    resp = response or make_fake_response()
    t = target or brief.target
    w = weights or brief.weights
    b = block or brief.objective_block
    m = compute_metrics(resp, t)
    params = V4Params.from_block(b)
    j, terms = objective_v4(m, resp, True, t, w, params)
    arrays = {
        "freqs_hz": np.asarray(resp.freqs_hz),
        "h_angles_deg": np.asarray(resp.h_angles_deg),
        "v_angles_deg": np.asarray(resp.v_angles_deg),
        "spl_h_db": np.asarray(resp.spl_h_db),
        "spl_v_db": np.asarray(resp.spl_v_db),
        "balloon_dirs": np.asarray(resp.balloon_dirs),
        "spl_balloon_db": np.asarray(resp.spl_balloon_db),
        "z_throat": np.asarray(resp.z_throat),
        "bw_h_deg": np.asarray(m.bw_h_deg),
        "bw_v_deg": np.asarray(m.bw_v_deg),
        "di_db": np.asarray(m.di_db),
        "ripple_h_db": np.asarray(m.ripple_h_db),
        "ripple_v_db": np.asarray(m.ripple_v_db),
        "on_axis_db": np.asarray(m.on_axis_db),
    }
    meta = {
        "ok": True,
        "design_hash": "design-1",
        "mesh_hash": "mesh-1",
        "solve_hash": "solve-1",
        "family": "OSSE",
        "params": {"L_mm": 260.0, "a_deg": 24.2},
        "mesh": {"n_triangles": 5000, "n_dof": 2598},
        "solve": {"backend": "fake", "n_dof": 2598, "freqs_hz": list(resp.freqs_hz),
                  "observation": {"distance_m": 2.0}},
        "excitation": {"kind": "uniform_normal_velocity"},
        "lib_shas": {"hornlab_mesher": "m" * 40},
        "metrics_scalars": dict(m.scalars),
        "objective": j,
        "terms": terms,
        "objective_version": 4,
        "target": dataclasses.asdict(t),
    }
    return meta, arrays, float(j), m, resp


# ------------------------------------------------------------------ brief resolution

def test_real_brief_resolves_through_the_production_loader(brief):
    assert brief.name == "native_ath_core_2in_v4"
    assert brief.objective_version == 4
    assert isinstance(brief.objective_params, V4Params)
    assert brief.objective_params.cov_narrow_ratio == 2.0
    assert brief.weights["diag"] == pytest.approx(0.5)
    t = brief.target
    assert (t.coverage_h_deg, t.coverage_v_deg) == (50.0, 50.0)
    assert (t.band_lo_hz, t.band_hi_hz) == (300.0, 8000.0)
    assert t.f0_effective_hz() == 1280.0


def test_brief_from_config_uses_config_resolution(brief):
    resolved = replay.brief_from_config(TYPOLOGY)
    # The full config resolver additionally surfaces the brief driver's exit radius on the
    # target; every scoring-relevant core field still matches the brief.
    assert (resolved.target.coverage_h_deg, resolved.target.coverage_v_deg) == (50.0, 50.0)
    assert (resolved.target.band_lo_hz, resolved.target.band_hi_hz) == (300.0, 8000.0)
    assert resolved.target.f0_effective_hz() == 1280.0
    assert resolved.target.driver_exit_radius_mm == 25.4
    assert resolved.objective_version == 4
    assert resolved.weights == brief.weights
    assert resolved.objective_params.cov_narrow_ratio == 2.0


# ------------------------------------------------------------------ original parity

def test_original_v4_replay_reproduces_stored_j(brief):
    meta, arrays, stored_j, _m, _r = _record(brief)
    res = replay.replay_record(meta, arrays, brief=brief)
    assert res.status == replay.STATUS_EXACT_COMPLETE
    assert res.reasons == ()
    assert res.metric_source == "stored"
    assert res.j == pytest.approx(stored_j, rel=0, abs=1e-9)
    assert res.parity_delta == pytest.approx(0.0, rel=0, abs=1e-9)
    assert res.diagnostics["ripple_used_response"] is True
    assert res.diagnostics["flat_used_response"] is True
    assert res.diagnostics["diag_available"] is True
    assert res.diagnostics["stored_metrics_used"] is True


def test_replay_accepts_a_brief_path(brief):
    meta, arrays, stored_j, _m, _r = _record(brief)
    res = replay.replay_record(meta, arrays, brief=str(BRIEF_PATH))
    assert res.j == pytest.approx(stored_j, abs=1e-9)
    assert res.status == replay.STATUS_EXACT_COMPLETE


def test_brief_target_is_the_scoring_target_not_the_stored_target(brief):
    """Parent gate test (M0 freeze section 2): a record whose stored target lacks the brief's
    optional freq_weights (2500-5500 Hz x2) is scored under the RESOLVED BRIEF when replaying
    with that brief; the stored target stays the original-parity comparator, and the score
    identity carries the brief's identity/hashes. Historical parity only applies when the
    requested and stored target keys are identical."""
    from conftest import make_fake_response

    # A frequency-independent pattern is indifferent to frequency weights by construction; give
    # the cuts a frequency-varying beam so the x2 band actually changes the cov term.
    resp2 = make_fake_response()
    freqs = np.asarray(resp2.freqs_hz, dtype=float)
    span = (freqs / freqs.max())
    lift_h = 3.0 * span[:, None] * (1.0 - np.cos(np.radians(np.abs(
        np.asarray(resp2.h_angles_deg, dtype=float)))))[None, :]
    lift_v = 2.5 * span[:, None] * (1.0 - np.cos(np.radians(np.abs(
        np.asarray(resp2.v_angles_deg, dtype=float)))))[None, :]
    resp2.spl_h_db = resp2.spl_h_db - lift_h
    resp2.spl_v_db = resp2.spl_v_db - lift_v

    stored_t = dataclasses.replace(brief.target, freq_weights=None)
    meta, arrays, stored_j, _m, _resp = _record(brief, target=stored_t, response=resp2)

    orig = replay.replay_record(meta, arrays, brief=brief, target=stored_t)
    assert orig.status == replay.STATUS_EXACT_COMPLETE
    assert orig.parity_delta == pytest.approx(0.0, abs=1e-9)
    assert orig.target["freq_weights"] is None

    base = replay.replay_record(meta, arrays, brief=brief)
    assert base.status == replay.STATUS_EXACT_COMPLETE
    assert base.target["freq_weights"] == {"band_hz": [[2500.0, 5500.0, 2.0]]}
    assert base.j != pytest.approx(orig.j)
    assert base.parity_delta is None          # targets differ -> never historical parity
    assert base.physical_id == orig.physical_id
    assert base.metric_id != orig.metric_id   # target-dependent metric identity
    assert base.score_id != orig.score_id
    assert "native_ath_core_2in_v4" == brief.name
    # The diagnostic surface separates the two worlds honestly.
    assert base.diagnostics["target_changed"] is True
    assert orig.diagnostics["target_changed"] is False


# ------------------------------------------------------------------ weight / tolerance-only

def test_weight_only_change_is_a_new_score_identity_only(brief):
    meta, arrays, stored_j, _m, _r = _record(brief)
    base = replay.replay_record(meta, arrays, brief=brief)
    w2 = dict(brief.weights)
    w2["di"] = 0.6
    changed = replay.replay_record(meta, arrays, brief=brief, weights=w2)
    assert changed.status == replay.STATUS_EXACT_COMPLETE
    assert changed.physical_id == base.physical_id
    assert changed.metric_id == base.metric_id
    assert changed.score_id != base.score_id
    assert changed.j == pytest.approx(changed.terms["total"])
    assert changed.j != pytest.approx(stored_j, abs=1e-9)
    assert changed.parity_delta is None


def test_tolerance_only_change_is_a_new_score_identity(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    base = replay.replay_record(meta, arrays, brief=brief)
    block = dict(brief.objective_block)
    block["tolerances"] = dict(block["tolerances"], cov=3.0)
    changed = replay.replay_record(meta, arrays, brief=brief, objective_params=block)
    assert changed.status == replay.STATUS_EXACT_COMPLETE
    assert changed.physical_id == base.physical_id
    assert changed.metric_id == base.metric_id
    assert changed.score_id != base.score_id
    assert changed.j != pytest.approx(base.j)


# ------------------------------------------------------------------ target change

def test_supported_target_change_regenerates_metrics(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    base = replay.replay_record(meta, arrays, brief=brief)
    t2 = dataclasses.replace(brief.target, coverage_h_deg=60.0, coverage_v_deg=45.0,
                             band_hi_hz=6000.0)
    changed = replay.replay_record(meta, arrays, brief=brief, target=t2)
    assert changed.status == replay.STATUS_EXACT_COMPLETE
    assert changed.physical_id == base.physical_id
    assert changed.metric_id != base.metric_id
    assert changed.score_id != base.score_id
    assert changed.metric_source == "regenerated"
    assert changed.diagnostics["target_changed"] is True
    assert changed.diagnostics["stored_metrics_used"] is False
    assert math.isfinite(changed.j)


def test_target_change_without_response_arrays_refuses(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    metrics_only = {k: v for k, v in arrays.items()
                    if k in ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db",
                             "ripple_v_db", "on_axis_db", "z_throat")}
    t2 = dataclasses.replace(brief.target, coverage_h_deg=60.0)
    res = replay.replay_record(meta, metrics_only, brief=brief, target=t2)
    assert res.status == replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    assert replay.R_TARGET_REGEN_UNSUPPORTED in res.reasons
    assert res.j is None


def test_target_change_outside_the_stored_band_refuses(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    t2 = Target.from_dict({
        "coverage_h_deg": 50.0, "coverage_v_deg": 50.0,
        "band_lo_hz": 300.0, "band_hi_hz": 400.0, "f0_hz": 350.0,
    })
    res = replay.replay_record(meta, arrays, brief=brief, target=t2)
    assert res.status == replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    assert replay.R_BAND_NOT_COVERED in res.reasons
    assert res.j is None


# ------------------------------------------------------------------ missing-input refusals

def test_metrics_only_replay_is_partial_not_exact(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    metrics_only = {k: v for k, v in arrays.items()
                    if k in ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db",
                             "ripple_v_db", "on_axis_db", "z_throat")}
    res = replay.replay_record(meta, metrics_only, brief=brief)
    assert res.status == replay.STATUS_PARTIAL_UNSUPPORTED
    assert replay.R_NO_RESPONSE in res.reasons
    assert replay.R_MISSING_BALLOON in res.reasons
    assert res.j is not None            # diagnostic only; never ranks as complete


def test_missing_balloon_with_weighted_diag_is_partial(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    no_balloon = {k: v for k, v in arrays.items()
                  if k not in ("balloon_dirs", "spl_balloon_db")}
    res = replay.replay_record(meta, no_balloon, brief=brief)
    assert res.status == replay.STATUS_PARTIAL_UNSUPPORTED
    assert replay.R_MISSING_BALLOON in res.reasons


def test_missing_impedance_with_active_load_refuses(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    no_z = {k: v for k, v in arrays.items() if k != "z_throat"}
    w2 = dict(brief.weights)
    w2["load"] = 0.5
    res = replay.replay_record(meta, no_z, brief=brief, weights=w2)
    assert res.status == replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    assert replay.R_MISSING_IMPEDANCE in res.reasons
    assert res.j is None


def test_unweighted_missing_impedance_is_not_a_loading_pass(brief):
    # load weight is 0 in the ATH brief, so a missing z is irrelevant to this score.
    meta, arrays, _stored_j, _m, _r = _record(brief)
    no_z = {k: v for k, v in arrays.items() if k != "z_throat"}
    res = replay.replay_record(meta, no_z, brief=brief)
    assert res.status == replay.STATUS_EXACT_COMPLETE


def test_meh_v5_requires_meh_inputs(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    res = replay.replay_record(meta, arrays, brief=brief, objective_version=5)
    assert res.status == replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    assert replay.R_REPLAY_VERSION_UNSUPPORTED in res.reasons
    assert res.j is None


def test_requested_throat_gate_refuses_without_stored_geometry(brief):
    gate_brief = dataclasses.replace(
        brief, raw={**brief.raw, "gates": {"round_throat": True}})
    meta, arrays, _stored_j, _m, _r = _record(brief)
    res = replay.replay_record(meta, arrays, brief=gate_brief)
    assert res.status == replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    assert replay.R_MISSING_THROAT in res.reasons
    assert res.j is None


# ------------------------------------------------------------------ ranking + determinism

def test_incomplete_rows_never_rank_beside_complete_rows(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    complete = replay.replay_record(meta, arrays, brief=brief)
    metrics_only = {k: v for k, v in arrays.items()
                    if k in ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db",
                             "ripple_v_db", "on_axis_db", "z_throat")}
    partial_meta = dict(meta, design_hash="design-2")
    partial = replay.replay_record(partial_meta, metrics_only, brief=brief)
    assert partial.j is not None
    ranked = replay.rank_complete([partial, complete])
    assert ranked == [complete]
    assert replay.incomplete_results([partial, complete]) == [partial]


def test_identity_hashes_are_deterministic(brief):
    meta, arrays, _stored_j, _m, _r = _record(brief)
    a = replay.replay_record(meta, arrays, brief=brief)
    b = replay.replay_record(meta, arrays, brief=brief)
    assert (a.physical_id, a.metric_id, a.score_id) == (b.physical_id, b.metric_id, b.score_id)
    assert a.to_dict() == b.to_dict()
    assert len(a.physical_id) == 64 and len(a.metric_id) == 64 and len(a.score_id) == 64


# ------------------------------------------------------------------ run-dir path

def test_replay_run_dir(tmp_path, brief):
    meta, arrays, stored_j, _m, resp = _record(brief)
    ddir = tmp_path / "designs" / "design-1"
    ddir.mkdir(parents=True)
    save_response(ddir / "response.npz", resp)
    payload = {
        "freqs_hz": list(arrays["freqs_hz"]),
        "bw_h_deg": list(arrays["bw_h_deg"]),
        "bw_v_deg": list(arrays["bw_v_deg"]),
        "di_db": list(arrays["di_db"]),
        "di_source": "balloon",
        "ripple_h_db": list(arrays["ripple_h_db"]),
        "ripple_v_db": list(arrays["ripple_v_db"]),
        "on_axis_db": list(arrays["on_axis_db"]),
        "z_throat_real": list(np.real(arrays["z_throat"])),
        "scalars": meta["metrics_scalars"],
    }
    (ddir / "metrics.json").write_text(
        __import__("json").dumps(payload), encoding="utf-8")
    res = replay.replay_run_dir(tmp_path, "design-1", brief=brief)
    assert res.status == replay.STATUS_EXACT_COMPLETE
    assert res.j == pytest.approx(stored_j, abs=1e-9)
