"""P0 read-only bridge: study observation -> persisted physical artifacts (offline, no GPU).

The resolver must map ``(study_id, root, package sha, design hash, solve id)`` to
``runs/study-<package16>/{screen|verify}/designs/<hash>/`` without ever accepting a client
filesystem path, and the GET routes must never reach a solve/verify/queue path.  These tests
build a small synthetic study whose ``screen`` and ``verify`` folders carry the ordinary
production artifacts (``mesh.msh``, ``metrics.json``, ``response.npz``, ``design.json``).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.gui import data as D
from hornlab_search.gui import study_designs as SD
from hornlab_search.gui.server import App
from hornlab_search.gui.study_index import StudyIndex
from hornlab_search.studies.schema import NotFound
from hornlab_search.studies.service import StudyService

MSH = (
    "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n"
    "$Nodes\n3\n"
    "1 0.0 0.0 0.0\n2 0.10 0.0 0.0\n3 0.0 0.10 0.0\n"
    "$EndNodes\n$Elements\n1\n"
    "1 2 2 0 0 1 2 3\n"
    "$EndElements\n"
)

MEASURED = "aaaaaaaaaaaa"
MESH_ONLY = "bbbbbbbbbbbb"
UNSUPPORTED = "cccccccccccc"
NO_DESIGN = "dddddddddddd"
STALE = "eeeeeeeeeeee"
PREVIEW = "ffffffffffff"


def _solve_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _metrics():
    return {
        "freqs_hz": [500.0, 1000.0],
        "bw_h_deg": [70.0, 60.0], "bw_v_deg": [45.0, 40.0],
        "di_db": [10.0, 11.0], "di_source": "balloon",
        "on_axis_db": [-1.0, -2.0],
        "ripple_h_db": [1.0, 1.2], "ripple_v_db": [0.8, 0.9],
        "z_throat_real": [1.0, 1.1], "scalars": {"di_mean_db": 10.5},
    }


def _write_response(design_dir: Path, *, balloon: bool = True) -> None:
    payload = dict(
        freqs_hz=np.array([500.0, 1000.0]),
        h_angles_deg=np.array([-90.0, -45.0, 0.0, 45.0, 90.0]),
        v_angles_deg=np.array([-90.0, -45.0, 0.0, 45.0, 90.0]),
        spl_h_db=np.zeros((2, 5)), spl_v_db=np.zeros((2, 5)),
        z_throat=np.ones(2, complex), n_dof=np.int64(42),
        meta=np.array(json.dumps({"balloon_grid": [3, 4],
                                  "balloon_layout": "theta-major",
                                  "distance_m": 2.0})),
    )
    if balloon:
        payload["spl_balloon_db"] = np.zeros((2, 12))
    np.savez_compressed(design_dir / "response.npz", **payload)


def _write_design(design_dir: Path, design_hash: str, *, mesh: bool = True,
                  metrics: bool = True, response: bool = True,
                  params: dict | None = None, with_balloon: bool = True) -> None:
    design_dir.mkdir(parents=True, exist_ok=True)
    record = {"design_hash": design_hash, "family": "OSSE",
              "params": params if params is not None else {"L_mm": 250.0, "a_deg": 40.0}}
    (design_dir / "design.json").write_text(json.dumps(record), encoding="utf-8")
    if mesh:
        (design_dir / "mesh.msh").write_text(MSH, encoding="utf-8")
    if metrics:
        (design_dir / "metrics.json").write_text(json.dumps(_metrics()), encoding="utf-8")
    if response:
        _write_response(design_dir, balloon=with_balloon)


def _fixture(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "runs" / "night" / "arm"
    service = StudyService(root)
    sid = service.create_study({"protocol": "bo-study-v1.1", "question": "bridge"},
                               "create")["id"]
    body = {"schema": "run-package-v1", "protocol": "bo-study-v1.1", "study_id": sid,
            "spec_revision": 1, "spec_hash": "0" * 64,
            "budget": {"screen_calls": 3, "verify_calls": 1}}
    content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package = service.attach_artifact(sid, 1, "package", content, {}, "package")
    sha = package["sha256"]
    with service.store.connect() as conn:
        conn.execute(
            "INSERT INTO packages(id,study_id,revision,package_json,active,cancelled,status,observation_seq) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (sha, sid, 1, content.decode("utf-8"), 0, 0, "pool_exhausted", 0))

    runs = repo / "runs"
    run_root = runs / ("study-" + sha[:16])
    for tier in ("screen", "verify"):
        tier_dir = run_root / tier
        tier_dir.mkdir(parents=True)
        (tier_dir / "config.yaml").write_text("{}\n", encoding="utf-8")
        (tier_dir / "run.json").write_text(json.dumps({
            "id": tier, "mode": tier, "study_id": sid, "package_id": sha,
            "objective_version": 7,
        }), encoding="utf-8")
        (tier_dir / "designs").mkdir()

    screen = run_root / "screen"
    verify = run_root / "verify"
    _write_design(screen / "designs" / MEASURED, MEASURED)
    _write_design(verify / "designs" / MEASURED, MEASURED)
    _write_design(screen / "designs" / MESH_ONLY, MESH_ONLY, metrics=False, response=False)
    _write_design(screen / "designs" / UNSUPPORTED, UNSUPPORTED,
                  mesh=False, metrics=False, response=False,
                  params={"cad": {"step": "horn.step"}})
    _write_design(screen / "designs" / PREVIEW, PREVIEW,
                  mesh=False, metrics=False, response=False,
                  params={"L_mm": 250.0, "a_deg": 40.0})
    _write_design(screen / "designs" / STALE, "abababababab", metrics=True, response=True)

    solves = {
        "measured": _solve_id("measured"),
        "mesh_only": _solve_id("mesh_only"),
        "unsupported": _solve_id("unsupported"),
        "no_design": _solve_id("no_design"),
        "stale": _solve_id("stale"),
        "preview": _solve_id("preview"),
        "verify": _solve_id("verify"),
    }
    params = {"L_mm": 250.0, "a_deg": 40.0}

    def attempt(key, design_hash, *, kind="screen", physical=True, j=3.0,
                candidate_params=None, outcome="success", physical_id=None, score_id=None):
        solve = solves[key]
        candidate = {"kind": kind, "solve_id": solve, "design_hash": design_hash}
        if candidate_params is not False:
            candidate["params"] = candidate_params if candidate_params is not None else params
        result = {"kind": kind, "solve_id": solve, "design_hash": design_hash,
                  "eligible": physical, "outcome": outcome,
                  "observed_j": j if physical else None,
                  "physical_measurement": physical,
                  "physical_id": physical_id or ("p-" + key),
                  "score_id": score_id or ("s-" + key)}
        with service.store.connect() as conn:
            conn.execute(
                "INSERT INTO attempts(id,study_id,package_id,solve_id,kind,candidate_json,reserved,status,result_json) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("att-" + key, sid, sha, solve, kind, json.dumps(candidate), 1,
                 "resolved", json.dumps(result)))
        return {"attempt_id": "att-" + key, "solve_id": solve,
                "physical_id": physical_id or ("p-" + key),
                "score_id": score_id or ("s-" + key)}

    rows = [
        attempt("measured", MEASURED, j=3.0),
        attempt("mesh_only", MESH_ONLY, j=3.5),
        attempt("unsupported", UNSUPPORTED, j=4.0),
        attempt("no_design", NO_DESIGN, j=4.5, candidate_params=False),
        attempt("stale", STALE, j=3.2),
        attempt("preview", PREVIEW, j=3.7),
    ]
    for seq, row in enumerate(rows, start=1):
        with service.store.connect() as conn:
            conn.execute(
                "INSERT INTO observations(study_id,package_id,observation_seq,attempt_id,physical_id,score_id) "
                "VALUES(?,?,?,?,?,?)",
                (sid, sha, seq, row["attempt_id"], row["physical_id"], row["score_id"]))
    # A verify attempt for the measured design (not an observation row; attached as evidence).
    attempt("verify", MEASURED, kind="verify", j=2.9)

    index = StudyIndex(repo, primary_root=runs / "studies", extra_roots=[root])
    root_id = index._root_id(root.resolve())
    return {"repo": repo, "runs": runs, "root": root, "root_id": root_id, "sid": sid,
            "sha": sha, "run_root": run_root, "solves": solves, "service": service,
            "index": index}


def _fake_materialize(*_args, **_kwargs):
    return {
        "inner_points": np.zeros((3, 3, 3)),
        "formula": "OSSE", "mode": "bare", "quadrants": "1",
        "resolution_mm": 20.0,
    }


def _fake_tessellate(*_args, **_kwargs):
    return {"roles": ["horn.inner"], "positions": np.zeros((3, 3)),
            "indices": np.array([0, 1, 2]), "warnings": []}


@pytest.fixture()
def study(tmp_path, monkeypatch):
    fx = _fixture(tmp_path)
    monkeypatch.setattr("hornlab_search.bo.data.materialize_geometry", _fake_materialize)
    monkeypatch.setattr("hornlab_search.config.load_config", lambda *a, **k: object())
    monkeypatch.setattr("hornlab_search.gui.preview.tessellate", _fake_tessellate)
    return fx


# --------------------------------------------------------------------------- listing


def test_listing_paginates_and_returns_typed_states(study):
    out = SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                          runs_root=study["runs"], page=1, page_size=10)
    assert out["status"] == "ok"
    assert out["n_total"] == 6
    assert out["n_pages"] == 1
    states = {row["design_hash"]: row["state"] for row in out["rows"]}
    assert states[MEASURED] == "measured"
    assert states[MESH_ONLY] == "geometry_only"
    assert states[UNSUPPORTED] == "unsupported_geometry"
    assert states[NO_DESIGN] == "missing_artifact"
    assert states[STALE] == "stale"
    assert states[PREVIEW] == "geometry_only"
    # Verify evidence is attached to the measured design, not duplicated as a candidate.
    measured = next(row for row in out["rows"] if row["design_hash"] == MEASURED)
    assert measured["verify"] == {"available": True, "j": 2.9,
                                  "solve_id": study["solves"]["verify"], "kind": "verify"}
    # The listing is small: it must not smuggle mesh/curve/balloon payloads.
    for row in out["rows"]:
        assert "geometry" not in row or row["geometry"] is None
        assert "curves" not in row and "balloon" not in row

    page3 = SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                            runs_root=study["runs"], page=3, page_size=2, sort="seq")
    assert len(page3["rows"]) == 2 and page3["n_pages"] == 3
    seqs = [row["observation_seq"] for row in page3["rows"]]
    assert seqs == [5, 6]


def test_listing_sorts_by_j_and_rejects_bad_paging(study):
    out = SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                          runs_root=study["runs"], sort="best_j")
    js = [row["j"] for row in out["rows"] if row["j"] is not None]
    assert js == sorted(js)
    with pytest.raises(ValueError):
        SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                        runs_root=study["runs"], page=0)
    with pytest.raises(ValueError):
        SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                        runs_root=study["runs"], page_size=101)
    with pytest.raises(ValueError):
        SD.observations(study["index"], study["sid"], root_id=study["root_id"],
                        runs_root=study["runs"], sort="nope")


# --------------------------------------------------------------------------- detail


def test_detail_reports_identity_and_tier_availability(study):
    out = SD.observation_detail(study["index"], study["sid"], study["solves"]["measured"],
                                root_id=study["root_id"], runs_root=study["runs"])
    assert out["state"] == "measured"
    assert out["tier"] == "screen" and out["kind"] == "screen"
    assert out["identities"]["design_hash"] == MEASURED
    assert out["identities"]["physical_id"] == "p-measured"
    assert out["artifact"]["mesh"] and out["artifact"]["response"]
    assert out["tiers"]["screen"]["state"] == "ok"
    assert out["tiers"]["verify"]["state"] == "ok"
    assert out["tiers"]["verify"]["design_dir"] is True
    assert out["verify"]["j"] == 2.9


# --------------------------------------------------------------------------- geometry


def test_geometry_reads_stored_mesh_and_labels_preview(study):
    stored = SD.geometry(study["index"], study["sid"], study["solves"]["measured"],
                         root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert stored["state"] == "measured" and stored["source"] == "stored_mesh"
    assert stored["preview"] is False
    assert len(stored["geometry"]["tris"]) == 3
    assert "profile" in stored and "profile_reason" in stored

    preview = SD.geometry(study["index"], study["sid"], study["solves"]["preview"],
                          root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert preview["state"] == "geometry_only"
    assert preview["source"] == "preview" and preview["preview"] is True
    assert "NOT the stored solved surface" in preview["notice"]
    assert preview["geometry"]["quadrants"] == "1"
    assert preview["geometry"]["tris"] == [0, 1, 2]


def test_geometry_unsupported_family_is_not_a_fake_horn(study):
    out = SD.geometry(study["index"], study["sid"], study["solves"]["unsupported"],
                      root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert out["state"] == "unsupported_geometry"
    assert out["geometry"] is None
    assert "CAD" in (out["reason"] or "")

    missing = SD.geometry(study["index"], study["sid"], study["solves"]["no_design"],
                          root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert missing["state"] == "missing_artifact" and missing["geometry"] is None

    stale = SD.geometry(study["index"], study["sid"], study["solves"]["stale"],
                        root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert stale["state"] == "stale" and stale["geometry"] is None
    stale_ac = SD.acoustics(study["index"], study["sid"], study["solves"]["stale"],
                            root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert stale_ac["state"] == "stale" and stale_ac["curves"] is None
    stale_bal = SD.balloon(study["index"], study["sid"], study["solves"]["stale"],
                           root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert stale_bal["state"] == "stale" and stale_bal["balloon"] is None


def test_geometry_verify_tier_and_tier_allowlist(study):
    out = SD.geometry(study["index"], study["sid"], study["solves"]["measured"],
                      root_id=study["root_id"], runs_root=study["runs"], tier="verify")
    assert out["state"] == "measured" and out["tier"] == "verify"
    with pytest.raises(ValueError, match="unknown tier"):
        SD.geometry(study["index"], study["sid"], study["solves"]["measured"],
                    root_id=study["root_id"], runs_root=study["runs"], tier="../screen")


def test_geometry_without_a_verify_folder_is_missing(study):
    # MESH_ONLY has no verify design; the verify tier must not fall back to the screen folder.
    out = SD.geometry(study["index"], study["sid"], study["solves"]["mesh_only"],
                      root_id=study["root_id"], runs_root=study["runs"], tier="verify")
    assert out["state"] in ("missing_artifact", "geometry_only")
    assert out["tier"] == "verify"


# --------------------------------------------------------------------------- acoustics / balloon


def test_acoustics_and_balloon_read_only_stored_arrays(study):
    curves = SD.acoustics(study["index"], study["sid"], study["solves"]["measured"],
                          root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert curves["state"] == "measured"
    assert curves["curves"]["freqs"] == [500.0, 1000.0]
    assert curves["curves"]["params"]["L_mm"] == 250.0
    assert curves["objective_version"] == 7
    assert curves["brief_name"] is None and curves["brief_sha256"] is None
    assert curves["identity_reason"]

    balloon = SD.balloon(study["index"], study["sid"], study["solves"]["measured"],
                         root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert balloon["state"] == "measured"
    assert balloon["balloon"]["balloon_grid"] == [3, 4]
    assert balloon["balloon"]["design"] == MEASURED

    # No stored acoustic arrays -> an explicit state, never an invented payload.
    absent = SD.acoustics(study["index"], study["sid"], study["solves"]["mesh_only"],
                          root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert absent["state"] == "geometry_only" and absent["curves"] is None
    absent_b = SD.balloon(study["index"], study["sid"], study["solves"]["mesh_only"],
                          root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert absent_b["state"] == "geometry_only" and absent_b["balloon"] is None


# --------------------------------------------------------------------------- security


def test_unknown_and_traversing_identifiers_are_refused(study):
    with pytest.raises(NotFound):
        SD.observation_detail(study["index"], study["sid"], "../../escape",
                              root_id=study["root_id"], runs_root=study["runs"])
    with pytest.raises(NotFound):
        SD.geometry(study["index"], study["sid"], "not-a-solve-id",
                    root_id=study["root_id"], runs_root=study["runs"])
    with pytest.raises(NotFound):
        SD.observations(study["index"], study["sid"], root_id="../../etc",
                        runs_root=study["runs"])
    ctx = SD._context(study["index"], study["sid"], study["root_id"], study["runs"])
    tier_dir = SD._tier_dir(ctx, "screen")
    with pytest.raises(ValueError):
        SD._design_dir(ctx, tier_dir, "../../escape")


def test_unrelated_study_cannot_read_this_observations(study):
    other = StudyService(study["repo"] / "runs" / "night" / "other")
    other_sid = other.create_study({"protocol": "bo-study-v1.1", "question": "other"},
                                   "create")["id"]
    index = StudyIndex(study["repo"], primary_root=study["runs"] / "studies")
    with pytest.raises(NotFound):
        SD.observation_detail(index, other_sid, study["solves"]["measured"],
                              runs_root=study["runs"])


def test_stale_package_identity_is_reported(study):
    run_json = study["run_root"] / "screen" / "run.json"
    data = json.loads(run_json.read_text(encoding="utf-8"))
    data["package_id"] = "0" * 64
    run_json.write_text(json.dumps(data), encoding="utf-8")
    out = SD.geometry(study["index"], study["sid"], study["solves"]["measured"],
                      root_id=study["root_id"], runs_root=study["runs"], tier="screen")
    assert out["state"] == "stale" and out["geometry"] is None


# --------------------------------------------------------------------------- GET routes, zero BEM


def test_get_routes_never_touch_solve_or_verify_paths(study, monkeypatch):
    calls = []

    def boom(*_args, **_kwargs):
        calls.append(1)
        raise AssertionError("a GET route reached a solve/verify/queue entry point")

    monkeypatch.setattr("hornlab_search.solve.base.get_backend", boom)
    monkeypatch.setattr("hornlab_search.search.evaluate.evaluate", boom)
    monkeypatch.setattr("hornlab_search.studies.production.execute_study", boom)
    monkeypatch.setattr("hornlab_search.studies.production.launch_study", boom)
    monkeypatch.setattr("hornlab_search.gui.study_jobs.StudyCpuJobs.submit", boom)
    monkeypatch.setattr("hornlab_search.gui.study_jobs.StudySolveDesignJobs.submit", boom)

    app = App(study["repo"], runs=study["runs"])
    sid, root_id = study["sid"], study["root_id"]
    solve_id = study["solves"]["measured"]

    listing = app.get(f"/api/studies/{sid}/observations",
                      {"root": [root_id], "page": ["1"], "page_size": ["5"],
                       "sort": ["best_j"]})
    assert listing["n_total"] == 6
    detail = app.get(f"/api/studies/{sid}/observations/{solve_id}", {"root": [root_id]})
    assert detail["state"] == "measured"
    geometry = app.get(f"/api/studies/{sid}/observations/{solve_id}/geometry",
                       {"root": [root_id], "tier": ["screen"]})
    assert geometry["state"] == "measured"
    verify = app.get(f"/api/studies/{sid}/observations/{solve_id}/geometry",
                     {"root": [root_id], "tier": ["verify"]})
    assert verify["tier"] == "verify"
    acoustics = app.get(f"/api/studies/{sid}/observations/{solve_id}/acoustics",
                        {"root": [root_id], "tier": ["screen"]})
    assert acoustics["curves"] is not None
    balloon = app.get(f"/api/studies/{sid}/observations/{solve_id}/balloon",
                      {"root": [root_id], "tier": ["screen"]})
    assert balloon["balloon"] is not None
    assert calls == []


def test_ordinary_timestamp_run_resolution_still_rejects_study_ids(study):
    with pytest.raises(ValueError):
        D._resolve_run(study["runs"], "study-" + study["sha"][:16])


# --------------------------------------------------------------------------- 219-row study


N_LARGE = 219
PREDICTED = "dddddddddddd"


def _large_j(index: int) -> float:
    return round(max(2.0, 4.0 - 0.05 * index), 6)


def _large_fixture(tmp_path: Path):
    repo = tmp_path / "large_repo"
    root = repo / "runs" / "night" / "large"
    service = StudyService(root)
    sid = service.create_study({"protocol": "bo-study-v1.1", "question": "large bridge",
                                "policy": {"proposal_policy": "scalar", "seed": 7}},
                               "create")["id"]
    body = {"schema": "run-package-v1", "protocol": "bo-study-v1.1", "study_id": sid,
            "spec_revision": 1, "spec_hash": "0" * 64,
            "budget": {"screen_calls": N_LARGE, "verify_calls": 3}}
    content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package = service.attach_artifact(sid, 1, "package", content, {}, "package")
    sha = package["sha256"]
    with service.store.connect() as conn:
        conn.execute(
            "INSERT INTO packages(id,study_id,revision,package_json,active,cancelled,status,observation_seq) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (sha, sid, 1, content.decode("utf-8"), 0, 0, "pool_exhausted", 0))
    service.attach_artifact(sid, 1, "snapshot", json.dumps({
        "task": {"brief_name": "large_brief", "brief_sha256": "a" * 64,
                 "config_name": "large_cfg", "objective_version": 7},
    }).encode("utf-8"), {}, "snapshot")

    runs = repo / "runs"
    run_root = runs / ("study-" + sha[:16])
    for tier in ("screen", "verify"):
        tier_dir = run_root / tier
        tier_dir.mkdir(parents=True)
        (tier_dir / "config.yaml").write_text(
            json.dumps({"family": "OSSE", "name": "large_cfg"}), encoding="utf-8")
        (tier_dir / "run.json").write_text(json.dumps({
            "id": tier, "mode": tier, "study_id": sid, "package_id": sha,
            "objective_version": 7, "name": "large_cfg",
        }), encoding="utf-8")
        (tier_dir / "designs").mkdir()

    screen = run_root / "screen"
    verify = run_root / "verify"
    for index in range(3):
        design = f"{index:012x}"
        _write_design(screen / "designs" / design, design)
        (screen / "designs" / design / "mesh_meta.json").write_text(json.dumps({
            "summary": {"bbox_m": [0.0, 0.0, 0.0, 0.30, 0.20, 0.10]},
            "result": {"bbox_m": [0.0, 0.0, 0.0, 0.30, 0.20, 0.10], "quadrants": "1"},
        }), encoding="utf-8")
    _write_design(verify / "designs" / f"{0:012x}", f"{0:012x}")

    solve_by_design = {}
    for index in range(N_LARGE):
        design = f"{index:012x}"
        solve = _solve_id(f"large-{index}")
        solve_by_design[design] = solve
        candidate = {"kind": "screen", "solve_id": solve, "design_hash": design,
                     "params": {"L_mm": 200.0 + index, "a_deg": 40.0}}
        if index == 0:
            candidate["descriptors"] = {"depth_mm": 100.0, "mouth_width_mm": 300.0,
                                        "throat_radius_mm": 18.0}
        result = {"kind": "screen", "solve_id": solve, "design_hash": design,
                  "eligible": True, "outcome": "success", "observed_j": _large_j(index),
                  "physical_measurement": True,
                  "physical_id": f"phys-{index}", "score_id": f"score-{index}"}
        if index < 4:
            coverage = [10.0, 9.0, 11.0, 12.0][index]
            ripple = [1.0, 1.2, 0.8, 1.3][index]
            result["pareto_metric"] = {"status": "complete", "coverage_deg": coverage,
                                       "ripple_db": ripple}
        with service.store.connect() as conn:
            conn.execute(
                "INSERT INTO attempts(id,study_id,package_id,solve_id,kind,candidate_json,reserved,status,result_json) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (f"att-{index}", sid, sha, solve, "screen", json.dumps(candidate), 1,
                 "resolved", json.dumps(result)))
            conn.execute(
                "INSERT INTO observations(study_id,package_id,observation_seq,attempt_id,physical_id,score_id) "
                "VALUES(?,?,?,?,?,?)",
                (sid, sha, index + 1, f"att-{index}", f"phys-{index}", f"score-{index}"))

    for index in (0, 5, 10):
        design = f"{index:012x}"
        solve = _solve_id(f"verify-{index}")
        candidate = {"kind": "verify", "solve_id": solve, "design_hash": design,
                     "params": {"L_mm": 200.0 + index, "a_deg": 40.0}}
        result = {"kind": "verify", "solve_id": solve, "design_hash": design,
                  "eligible": False, "outcome": "success",
                  "observed_j": _large_j(index) - 0.2, "physical_measurement": True,
                  "physical_id": f"vphys-{index}", "score_id": f"vscore-{index}"}
        with service.store.connect() as conn:
            conn.execute(
                "INSERT INTO attempts(id,study_id,package_id,solve_id,kind,candidate_json,reserved,status,result_json) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (f"att-verify-{index}", sid, sha, solve, "verify", json.dumps(candidate), 1,
                 "resolved", json.dumps(result)))

    predicted_solve = _solve_id("large-predicted")
    with service.store.connect() as conn:
        conn.execute(
            "INSERT INTO attempts(id,study_id,package_id,solve_id,kind,candidate_json,reserved,status,result_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            ("att-predicted", sid, sha, predicted_solve, "screen", json.dumps({
                "kind": "screen", "solve_id": predicted_solve, "design_hash": PREDICTED,
                "params": {"L_mm": 250.0},
                "predicted": {"j_mean": 3.1, "interval_label": "model credible interval"},
            }), 1, "reserved", None))

    index = StudyIndex(repo, primary_root=runs / "studies", extra_roots=[root])
    return {"repo": repo, "runs": runs, "root": root, "root_id": index._root_id(root.resolve()),
            "sid": sid, "sha": sha, "index": index, "solve_by_design": solve_by_design,
            "predicted_solve": predicted_solve}


@pytest.fixture()
def large_study(tmp_path, monkeypatch):
    fx = _large_fixture(tmp_path)
    monkeypatch.setattr("hornlab_search.bo.data.materialize_geometry", _fake_materialize)
    monkeypatch.setattr("hornlab_search.config.load_config", lambda *a, **k: object())
    monkeypatch.setattr("hornlab_search.gui.preview.tessellate", _fake_tessellate)
    return fx


def _all_pages(fx, page_size=25, **kwargs):
    first = SD.observations(fx["index"], fx["sid"], root_id=fx["root_id"],
                            runs_root=fx["runs"], page=1, page_size=page_size, **kwargs)
    rows = list(first["rows"])
    for page in range(2, first["n_pages"] + 1):
        rows.extend(SD.observations(fx["index"], fx["sid"], root_id=fx["root_id"],
                                    runs_root=fx["runs"], page=page,
                                    page_size=page_size, **kwargs)["rows"])
    return first, rows


def test_large_listing_pagination_covers_every_observation_exactly(large_study):
    first, rows = _all_pages(large_study)
    assert first["n_total"] == N_LARGE and first["n_unfiltered"] == N_LARGE + 1
    assert first["n_pages"] == 9
    solve_ids = [row["solve_id"] for row in rows]
    assert len(solve_ids) == N_LARGE
    assert len(set(solve_ids)) == N_LARGE
    assert set(solve_ids) == set(large_study["solve_by_design"].values())
    # The unobserved predicted marker is excluded by default and never a candidate.
    assert large_study["predicted_solve"] not in set(solve_ids)


def test_large_listing_field_derivations(large_study):
    _first, rows = _all_pages(large_study, page_size=100, sort="seq")
    by_design = {row["design_hash"]: row for row in rows}
    first = by_design["000000000000"]
    assert first["state"] == "measured"
    assert first["dimensions"]["mouth_w_mm"] > 0 and first["dimensions_reason"] is None
    assert first["descriptors"]["mouth_width_mm"] == 300.0
    assert first["descriptors_reason"] is None
    assert first["family"] == "OSSE"
    assert first["typology"] is None and "OSSE" in first["typology_reason"]
    assert first["new_incumbent"] is True and first["incumbent_reason"] is None
    assert first["pareto"] is True and first["nondominated"] is True
    assert first["verified_j"] is not None and first["screen_j"] is not None

    later = by_design["000000000007"]
    assert later["state"] == "geometry_only"
    assert later["dimensions"] is None and later["dimensions_reason"]
    assert later["descriptors"] is None and later["descriptors_reason"]
    assert later["pareto"] is False and later["pareto_reason"]
    assert later["family"] == "OSSE" and later["typology"] is None
    assert later["verified_j"] is None and later["screen_j"] is not None


def test_large_listing_sorts_and_filters(large_study):
    _sfirst, screen_rows = _all_pages(large_study, page_size=100, sort="screen_j")
    scores = [row["screen_j"] for row in screen_rows]
    assert scores == sorted(scores) and all(score is not None for score in scores)

    _vfirst, verified_rows = _all_pages(large_study, page_size=100, sort="verified_j")
    verified = [row["verified_j"] for row in verified_rows]
    assert verified[:3] == [pytest.approx(3.3), pytest.approx(3.55), pytest.approx(3.8)]
    assert all(value is None for value in verified[3:])

    only_verified = SD.observations(large_study["index"], large_study["sid"],
                                    root_id=large_study["root_id"], runs_root=large_study["runs"],
                                    verified=True)
    assert only_verified["n_total"] == 3 and all(row["verify"] for row in only_verified["rows"])
    unverified = SD.observations(large_study["index"], large_study["sid"],
                                 root_id=large_study["root_id"], runs_root=large_study["runs"],
                                 verified=False)
    assert unverified["n_total"] == N_LARGE - 3

    measured = SD.observations(large_study["index"], large_study["sid"],
                               root_id=large_study["root_id"], runs_root=large_study["runs"],
                               state=["measured"])
    assert measured["n_total"] == 3
    both = SD.observations(large_study["index"], large_study["sid"],
                           root_id=large_study["root_id"], runs_root=large_study["runs"],
                           state="measured,geometry_only")
    assert both["n_total"] == N_LARGE

    frontier = SD.observations(large_study["index"], large_study["sid"],
                               root_id=large_study["root_id"], runs_root=large_study["runs"],
                               nondominated=True)
    assert frontier["n_total"] == 3
    assert all(row["nondominated"] for row in frontier["rows"])
    pareto_rows = SD.observations(large_study["index"], large_study["sid"],
                                  root_id=large_study["root_id"], runs_root=large_study["runs"],
                                  pareto=True)
    assert pareto_rows["n_total"] == 4
    assert all(row["pareto"] for row in pareto_rows["rows"])

    expected_incumbents = 0
    best = None
    for index in range(N_LARGE):
        value = _large_j(index)
        if best is None or value < best:
            expected_incumbents += 1
            best = value
    incumbents = SD.observations(large_study["index"], large_study["sid"],
                                 root_id=large_study["root_id"], runs_root=large_study["runs"],
                                 new_incumbent=True)
    assert incumbents["n_total"] == expected_incumbents

    found = SD.observations(large_study["index"], large_study["sid"],
                            root_id=large_study["root_id"], runs_root=large_study["runs"],
                            q="000000000007")
    assert found["n_total"] == 1
    assert found["rows"][0]["design_hash"] == "000000000007"
    reason_q = SD.observations(large_study["index"], large_study["sid"],
                               root_id=large_study["root_id"], runs_root=large_study["runs"],
                               q="no-bem geometry preview")
    assert reason_q["n_total"] == N_LARGE - 3
    assert reason_q["filters"]["q"] == "no-bem geometry preview"

    predicted_first, predicted_rows = _all_pages(large_study, page_size=100,
                                                 include_predicted=True, sort="seq")
    assert predicted_first["n_total"] == N_LARGE + 1
    predicted = next(row for row in predicted_rows
                     if row["solve_id"] == large_study["predicted_solve"])
    assert predicted["state"] == "predicted_only" and predicted["bound_preview"] is True

    with pytest.raises(ValueError):
        SD.observations(large_study["index"], large_study["sid"],
                        root_id=large_study["root_id"], runs_root=large_study["runs"],
                        state=["not_a_state"])


def test_large_envelopes_expose_identity_and_profile(large_study):
    solve = large_study["solve_by_design"]["000000000000"]
    curves = SD.acoustics(large_study["index"], large_study["sid"], solve,
                          root_id=large_study["root_id"], runs_root=large_study["runs"],
                          tier="screen")
    assert curves["state"] == "measured"
    assert curves["objective_version"] == 7
    assert curves["brief_name"] == "large_brief"
    assert curves["brief_sha256"] == "a" * 64
    assert curves["config_name"] == "large_cfg"
    assert curves["identity_reason"] is None

    geometry = SD.geometry(large_study["index"], large_study["sid"], solve,
                           root_id=large_study["root_id"], runs_root=large_study["runs"],
                           tier="screen")
    assert geometry["state"] == "measured"
    assert "profile" in geometry and "profile_reason" in geometry
    assert geometry["profile"] is not None and geometry["profile_reason"] is None

    # A design with no stored acoustics has no profile and says why (never fabricated).
    other = large_study["solve_by_design"]["000000000007"]
    geometry2 = SD.geometry(large_study["index"], large_study["sid"], other,
                            root_id=large_study["root_id"], runs_root=large_study["runs"],
                            tier="screen")
    assert geometry2["profile"] is None and geometry2["profile_reason"]


def test_large_listing_convergence_identities_are_parallel(large_study):
    out = SD.observations(large_study["index"], large_study["sid"],
                          root_id=large_study["root_id"], runs_root=large_study["runs"],
                          page=1, page_size=5)
    convergence = out["convergence"]
    assert convergence["objective_version"] == 7
    arm = convergence["arms"][0]
    assert len(arm["solves"]) == N_LARGE
    assert len(arm["identities"]) == N_LARGE
    expected = large_study["solve_by_design"]
    for point, identity in zip(arm["solves"], arm["identities"]):
        assert isinstance(point[0], int) and isinstance(point[1], float)
        assert expected[identity["design_hash"]] == identity["solve_id"]
    assert len(arm["verify_points"]) == 3
    assert len(arm["verify_identities"]) == 3
    assert arm["verify_identities"][0]["design_hash"] == "000000000000"


def test_large_listing_app_route_composes_filters(large_study):
    app = App(large_study["repo"], runs=large_study["runs"])
    sid, root_id = large_study["sid"], large_study["root_id"]
    out = app.get(f"/api/studies/{sid}/observations",
                  {"root": [root_id], "sort": ["verified_j"], "verified": ["true"],
                   "state": ["measured,geometry_only"], "page_size": ["50"],
                   "include_predicted": ["false"]})
    assert out["n_total"] == 3
    assert out["filters"]["verified"] is True
    assert out["filters"]["include_predicted"] is False
    assert out["filters"]["state"] == ["measured", "geometry_only"]
    q = app.get(f"/api/studies/{sid}/observations",
                {"root": [root_id], "q": ["000000000007"]})
    assert q["n_total"] == 1

