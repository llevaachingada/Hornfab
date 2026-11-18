"""WP3 (2026-11-17): brief-truth replay laboratory contracts.

Pinned here:

* the two named legacy designs replay through the canonical pathway to their captured J and
  per-term values at floating precision (exact zero delta), and the read-only source files are
  unchanged afterwards;
* cross-version / cross-brief pooling of raw J is refused with a typed error, while a
  same-brief ranking is allowed;
* every OFFLINE/NOT-QUEUED v9 candidate YAML loads through the implemented schema
  (``config.load_brief`` -> ``Target.from_dict``), including the slope-weight-0 variant;
* ``objective.bw8k_floor`` is refused under v9 by the config layer and by the tool, while an
  explicit ``hf_floor`` remains the supported HF penalty channel;
* a v9 cross-target cell recomputes target-dependent metrics and reports diag/distd raw and
  unweighted (no stored ripple/diag/floor reuse).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from hornlab_search.config import ConfigError, load_brief
from hornlab_search.objective.replay import load_brief_context
from hornlab_search.objective.scalar_v9 import V9Params, objective_v9
from hornlab_search.targets.spec import Target
from tools.analysis import brief_truth_replay as BTR

ROOT = Path(__file__).resolve().parents[1]
#: Committed evidence copies first (present in a clean checkout); the gitignored scratch lane is
#: only a local fallback.  The candidate YAMLs themselves are committed under docs/evidence/.
_COMMITTED_CANDIDATES = ROOT / "docs" / "evidence" / "home_crowe_v9_offline_2026-11-17"
_SCRATCH_CANDIDATES = ROOT / "scratch" / "home_v9_offline_2026-11-17"
_CANDIDATE_DIR = (_COMMITTED_CANDIDATES
                  if sorted(_COMMITTED_CANDIDATES.glob("*.yaml")) else _SCRATCH_CANDIDATES)
CANDIDATES = sorted(_CANDIDATE_DIR.glob("*.yaml"))

LEGACY = ROOT / "runs" / "20261115T205453Z-screen-32f7c4"
KLANG = ROOT / "runs" / "20261116T225543Z-screen-6acf41"
C221 = ROOT / "runs" / "20261116T153619Z-screen-c221aa"
C221_HASH = "6d6dd332b282"
HAS_ARCHIVE = (LEGACY / "designs" / "22365b569be9" / "response.npz").is_file() and \
    (KLANG / "designs" / "491efb2132b8" / "response.npz").is_file()
HAS_C221_PAIR = ((C221 / "designs" / C221_HASH / "response.npz").is_file()
                 and (C221 / "verify" / "designs" / C221_HASH / "response.npz").is_file())

needs_archive = pytest.mark.skipif(
    not HAS_ARCHIVE,
    reason="requires the local run archive (runs/ is not part of the repo checkout)")
needs_c221 = pytest.mark.skipif(
    not HAS_C221_PAIR,
    reason="requires the local c221aa screen/verify pair (runs/ is local-only)")
needs_candidates = pytest.mark.skipif(
    not CANDIDATES,
    reason="no committed or scratch candidate v9 YAMLs found")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ candidate briefs


@needs_candidates
def test_candidate_yamls_exist_and_use_the_implemented_schema():
    assert CANDIDATES, "no v9 candidate YAMLs found under scratch/home_v9_offline_2026-11-17"
    onsets = set()
    for path in CANDIDATES:
        text = path.read_text(encoding="utf-8")
        assert "frequency_envelope:" not in text, (
            f"{path.name}: the 2026-11-16 RFC's early frequency_envelope syntax is historical "
            "and must not be used")
        assert "NOT-QUEUED" in text and "[proposed]" in text, (
            f"{path.name}: every candidate must be labelled NOT-QUEUED / [proposed]")
        raw = load_brief(path)                       # the real loader validates the YAML
        target = Target.from_dict(dict(raw["target"]))
        params = V9Params.from_block(dict(raw["objective"]))
        assert raw["objective"]["version"] == 9
        assert target.coverage_profile_mode == "corridor"
        assert target.coverage_profile_interpolation == "log_frequency"
        assert params.cov_v_weight == 0.5 and params.flat_band == "scored"
        assert "bw8k_floor" not in raw["objective"]
        # H corridor 60-90 deg allowance, preferred inside the owner's 70-90 interest range
        for hz, pref, lo, hi in target.coverage_profile_h:
            assert lo == 60.0 and hi == 90.0 and 70.0 <= pref <= 90.0
        # V corridor 40-60 deg allowance, constant 50 deg preferred
        for hz, pref, lo, hi in target.coverage_profile_v:
            assert hi == 60.0 and lo == 40.0 and pref == 50.0
        onsets.add(float(target.f0_v_hz))
        # descriptive nominal is carried separately from the scored corridor
        assert target.coverage_h_deg == 80.0 and target.coverage_v_deg == 50.0
    assert onsets == {700.0, 1000.0, 1250.0}


@needs_candidates
def test_slope_weight_zero_variant_is_declared_and_differs_only_in_that_weight():
    by_name = {p.stem: p for p in CANDIDATES}
    base = load_brief(by_name["home_v9_corridor_h90_70_v1000"])
    slope0 = load_brief(by_name["home_v9_corridor_h90_70_v1000_slope0"])
    assert float(slope0["weights"]["dislope"]) == 0.0
    assert float(base["weights"]["dislope"]) != 0.0
    assert {k: v for k, v in slope0["weights"].items() if k != "dislope"} == \
        {k: v for k, v in base["weights"].items() if k != "dislope"}
    assert slope0["target"] == base["target"] and slope0["objective"] == base["objective"]


def test_bw8k_floor_is_refused_under_v9_by_block_and_by_the_tool():
    block = {"version": 9, "bw8k_floor": 0.75,
             "tolerances": {k: 1.0 for k in
                            ("cov_profile", "rip", "flat", "load", "dislope",
                             "di_roughness", "flat_cv")}}
    with pytest.raises(ValueError, match="bw8k_floor"):
        V9Params.from_block(block)
    with pytest.raises(BTR.ScoreRuleError, match="bw8k_floor"):
        BTR.refuse_bw8k_floor_under_v9(9, block)
    # v7 is unaffected: the floor is that objective's legitimate constant.
    assert BTR.refuse_bw8k_floor_under_v9(7, {"version": 7, "bw8k_floor": 0.75}) is None


@needs_candidates
def test_bw8k_floor_is_refused_under_v9_by_config(tmp_path):
    src = CANDIDATES[0]
    text = src.read_text(encoding="utf-8")
    bad = text.replace("  lfp_crossover_ratio: 1.6\n",
                       "  lfp_crossover_ratio: 1.6\n  bw8k_floor: 0.75\n")
    assert "bw8k_floor" in bad and bad != text
    path = tmp_path / "bad_v9.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ConfigError, match="bw8k_floor"):
        load_brief(path)


def test_v9_hf_floor_is_accepted_as_its_own_weighted_term():
    block = {"version": 9,
             "tolerances": {k: 1.0 for k in
                            ("cov_profile", "rip", "flat", "load", "dislope",
                             "di_roughness", "flat_cv")},
             "hf_floor": {"hz": 8000.0, "h_deg": 48.0, "v_deg": 30.0,
                          "weight": 1.0, "tolerance": 2.0}}
    params = V9Params.from_block(block)
    assert "hf_floor" in params.weighted_keys()
    assert params.hf_floor["tolerance"] == 2.0


# ------------------------------------------------------------------ ranking refusals


def _row(version, brief_hash, j, design="d1"):
    return {"objective_version": version, "brief_hash": brief_hash, "J": j,
            "design_hash": design, "brief_name": f"b{brief_hash}"}


def test_pooled_ranking_refuses_cross_version():
    rows = [_row(7, "aaaa", 1.0, "crowe"), _row(9, "aaaa", 1.0, "crowe")]
    with pytest.raises(BTR.CrossVersionRankingRefused, match="not a common ranking"):
        BTR.pooled_ranking(rows)


def test_pooled_ranking_refuses_cross_brief_even_within_one_version():
    rows = [_row(9, "aaaa", 1.0, "crowe"), _row(9, "bbbb", 2.0, "klang")]
    with pytest.raises(BTR.CrossVersionRankingRefused):
        BTR.pooled_ranking(rows)
    # Same brief + same version is the one allowed ranking.
    ranked = BTR.pooled_ranking([_row(9, "aaaa", 2.0, "a"), _row(9, "aaaa", 1.0, "b")])
    assert [r["design_hash"] for r in ranked] == ["b", "a"]
    # rows without J never rank
    assert BTR.pooled_ranking([_row(9, "aaaa", None)]) == []


def test_rank_within_brief_attaches_ranks_and_refuses_mixed_versions():
    rows = [_row(9, "aaaa", 2.0, "a"), _row(9, "aaaa", 1.0, "b"),
            _row(9, "bbbb", 5.0, "a"), _row(9, "bbbb", 3.0, "b")]
    BTR.rank_within_brief(rows)
    assert [(r["design_hash"], r["rank_in_brief"]) for r in rows[:2]] == [("a", 2), ("b", 1)]
    with pytest.raises(BTR.CrossVersionRankingRefused):
        BTR.rank_within_brief([_row(7, "aaaa", 1.0, "a"), _row(9, "aaaa", 2.0, "b")])


# ------------------------------------------------------------------ legacy identity


@needs_archive
def test_identity_replay_reproduces_stored_j_exactly_and_does_not_mutate_sources(tmp_path):
    sources = [LEGACY / "designs" / "22365b569be9" / "response.npz",
               KLANG / "designs" / "491efb2132b8" / "response.npz",
               LEGACY / "best.json", KLANG / "best.json"]
    before = {str(p): _sha(p) for p in sources}
    payload = BTR.identity(tmp_path, BTR._default_designs())
    after = {str(p): _sha(p) for p in sources}
    assert before == after, "identity replay mutated a stored run/result file"

    assert payload["reproduced_nov17"] is True
    rows = {r["design"]: r for r in payload["identity"]}
    assert rows["crowe_es600"]["stored_J"] == 16.91817613526687
    assert rows["klangfilm_lame"]["stored_J"] == 8.923616737684702
    for row in rows.values():
        assert row["passed"] is True
        assert abs(row["delta"]) <= BTR.IDENTITY_REL_TOL * max(abs(row["stored_J"]), 1.0)
        assert row["max_abs_term_delta"] <= BTR.IDENTITY_TERM_TOL
        assert row["metrics_recomputed"] is True
    assert payload["matrix"]["crowe_es600"]["base"]["J"] != payload["matrix"]["crowe_es600"]["smooth"]["J"]
    assert (tmp_path / "identity_replay.json").is_file()


# ------------------------------------------------------------------ v9 scoring view


@needs_archive
@needs_candidates
def test_v9_cross_target_cell_recomputes_metrics_and_keeps_diag_raw_unweighted():
    from hornlab_search.solve.cache import load_response

    brief = load_brief_context(CANDIDATES[0])
    run = LEGACY
    h = "22365b569be9"
    resp = load_response(run / "designs" / h / "response.npz")
    result = BTR._replay(run, h, brief, config_path=run / "config.yaml")
    assert result.status == "exact_complete"
    assert result.diagnostics["target_changed"] is True
    assert result.diagnostics["stored_metrics_used"] is False
    cell = BTR.build_cell(resp, brief, result, label="crowe_es600", design_hash=h,
                          run_dir=run, source="test")
    assert cell["metrics_recomputed"] is True
    assert cell["target_changed"] is True
    assert cell["objective_version"] == 9
    by_key = {r["key"]: r for r in cell["terms"]}
    for key in ("cov_profile", "rip", "flat", "load", "dislope", "di_roughness", "flat_cv"):
        assert key in by_key and by_key[key]["contribution"] is not None
    assert by_key["diag"]["unweighted_raw"] is True and by_key["diag"]["contribution"] == 0.0
    assert by_key["distd"]["unweighted_raw"] is True and by_key["distd"]["weight"] == 0.0
    # J is the sum of the weighted contributions, not of the raw diagnostics.
    total = sum(r["contribution"] for r in cell["terms"])
    assert total == pytest.approx(cell["J"], abs=1e-9)
    # v9 scores no DI level; only the slope term exists.
    assert cell["facts"]["di"]["level_source"] is None
    assert cell["facts"]["diag_scored"] is False
    assert "bw8k_floor refused under v9" in cell["facts"]["bw8k_condition"]


@needs_archive
@needs_candidates
def test_scenario_matrix_refuses_cross_brief_pooling(tmp_path):
    briefs = [CANDIDATES[0], CANDIDATES[1]]
    payload = BTR.scenarios(briefs, [dict(BTR.LEGACY_DESIGNS[0])], tmp_path)
    assert len(payload["cells"]) == 2
    assert payload["cross_brief_ranking_refused"], "cross-brief pooling must be refused"
    assert payload["source_guard"]["unchanged"] is True
    matrix = json.loads((tmp_path / "replay_matrix.json").read_text(encoding="utf-8"))
    assert len(matrix["cells"]) == 2
    assert (tmp_path / "replay_terms.csv").is_file()


@needs_archive
@needs_candidates
def test_scenarios_accept_a_bare_response_npz(tmp_path):
    rp = LEGACY / "designs" / "22365b569be9" / "response.npz"
    design = {"label": "bare_crowe", "run": str(rp.parent), "design_hash": rp.parent.name,
              "response": str(rp), "own_cell": None}
    payload = BTR.scenarios([CANDIDATES[1]], [design], tmp_path)
    assert len(payload["cells"]) == 1
    cell = payload["cells"][0]
    assert cell["status"] == "exact_complete"
    assert cell["source"] == "v9-scenario-file"
    assert cell["J"] == pytest.approx(9.57672093289535, abs=1e-12)
    assert cell["stored_J"] is None


@needs_candidates
def test_dense_grid_brief_is_v9_only_and_changes_score_identity():
    v9 = load_brief_context(CANDIDATES[0])
    dense = BTR._grid_brief(v9, 58)
    assert dense.objective_params.score_grid == {"kind": "dense_log", "points": 58}
    assert dense.objective_block["score_grid"]["points"] == 58
    v7 = BTR._load_brief(BTR.BASE_BRIEF)
    with pytest.raises(BTR.ScoreRuleError, match="v9"):
        BTR._grid_brief(v7, 58)


def test_objective_v9_is_the_only_dispatched_scorer_and_never_raises():
    # The tool must not re-implement J: a malformed metrics object still returns the canonical
    # failure penalty from objective_v9 rather than raising.
    from hornlab_search.objective.terms import PENALTY_FAILED

    target = Target.from_dict({
        "coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
        "band_lo_hz": 350.0, "band_hi_hz": 8000.0, "di_target_db": None,
        "f0_hz": 700.0, "f0_v_hz": 1000.0,
        "coverage_profile": {
            "mode": "target", "interpolation": "log_frequency",
            "h": [{"hz": 700.0, "preferred_deg": 80.0}],
            "v": [{"hz": 1000.0, "preferred_deg": 50.0}]},
    })
    params = V9Params.from_block({
        "version": 9,
        "tolerances": {k: 1.0 for k in
                       ("cov_profile", "rip", "flat", "load", "dislope",
                        "di_roughness", "flat_cv")}})
    j, terms = objective_v9(None, None, False, target, {}, params)
    assert j == PENALTY_FAILED
    assert terms["total"] == j and terms["penalty"] == j
    assert "cov_profile" in terms and "di_roughness" in terms


# ------------------------------------------------------------------ hardening regressions

def test_identity_term_residuals_refuse_a_vacuous_comparison():
    with pytest.raises(BTR.IdentityReplayError, match="vacuous identity"):
        BTR._term_residuals({}, {"cov": 1.0})
    with pytest.raises(BTR.IdentityReplayError, match="vacuous identity"):
        BTR._term_residuals({"cov": 1.0}, {"rip": 2.0})
    assert BTR._term_residuals({"cov": 1.0, "rip": 2.0}, {"cov": 1.5, "rip": 2.0}) == {
        "cov": 0.5, "rip": 0.0}


@needs_archive
def test_run_read_paths_hash_best_metrics_and_response():
    paths = BTR._run_read_paths(LEGACY, "22365b569be9")
    names = {p.name for p in paths}
    assert {"best.json", "metrics.json", "response.npz", "config.yaml"} <= names


@needs_archive
@needs_candidates
def test_source_guard_snapshots_before_any_response_or_best_read(tmp_path, monkeypatch):
    events: list[str] = []
    real_hash = BTR._source_hashes
    real_best = BTR._load_best

    def spy_hash(paths):
        events.append("hash")
        return real_hash(paths)

    def spy_best(run_dir):
        events.append("best")
        return real_best(run_dir)

    import hornlab_search.solve.cache as cache

    real_load = cache.load_response

    def spy_load(path):
        events.append("load_response")
        return real_load(path)

    monkeypatch.setattr(BTR, "_source_hashes", spy_hash)
    monkeypatch.setattr(BTR, "_load_best", spy_best)
    monkeypatch.setattr(cache, "load_response", spy_load)

    BTR.scenarios([CANDIDATES[0]], [dict(BTR.LEGACY_DESIGNS[0])], tmp_path)
    assert events[0] == "hash", f"first filesystem action was {events[0]!r}, not the hash guard"
    first_read = next(i for i, event in enumerate(events) if event != "hash")
    assert all(event == "hash" for event in events[:first_read])
    assert events.count("hash") >= 2          # pre-read snapshot + final unchanged check


@needs_candidates
def test_grid_skips_a_pair_whose_response_side_is_missing(tmp_path):
    run = tmp_path / "synthetic-run"
    (run / "designs" / "deadbeef").mkdir(parents=True)
    (run / "verify" / "designs" / "deadbeef").mkdir(parents=True)
    # Screen side exists (presence is all the discovery check reads); verify side is absent.
    (run / "designs" / "deadbeef" / "response.npz").write_bytes(b"")

    payload = BTR.grid_stability(CANDIDATES[0], [run], tmp_path / "out")
    assert payload["pairs"] == 1
    assert payload["processed_pairs"] == 0
    assert payload["skipped_pairs"] == [{
        "run": "synthetic-run",
        "design_hash": "deadbeef",
        "missing_response_sides": ["verify"],
        "note": ("typed skip: no response.npz on verify; this pair contributes no J and is "
                 "not scored"),
    }]
    assert payload["sides"] == {}


@needs_candidates
def test_bad_v9_brief_exits_2_with_one_typed_line(tmp_path, capsys):
    text = CANDIDATES[0].read_text(encoding="utf-8")
    bad = text.replace("  lfp_crossover_ratio: 1.6\n",
                       "  lfp_crossover_ratio: 1.6\n  bw8k_floor: 0.75\n")
    assert bad != text and "bw8k_floor" in bad
    path = tmp_path / "bad_v9.yaml"
    path.write_text(bad, encoding="utf-8")
    rc = BTR.main(["scenarios", "--briefs", str(path), "--out", str(tmp_path / "out")])
    lines = [ln for ln in capsys.readouterr().err.strip().splitlines() if ln.strip()]
    assert rc == 2
    assert len(lines) == 1, lines
    assert "ConfigError" in lines[0]


@needs_c221
def test_grid_side_mesh_evidence_comes_from_stored_manifests():
    screen = BTR._mesh_side_record(C221, C221_HASH)
    verify = BTR._mesh_side_record(C221 / "verify", C221_HASH)
    for rec in (screen, verify):
        assert len(rec["mesh_hash"]) == 64
        assert rec["mesh_epw"] == pytest.approx(6.0)
        assert rec["n_dof"] == "unavailable" or isinstance(rec["n_dof"], int)
        assert rec["mesh_meta_key"] != "unavailable"
    # The verify manifest points at the same stored mesh, so "same-mesh" is evidenced now.
    assert screen["mesh_hash"] == verify["mesh_hash"]
