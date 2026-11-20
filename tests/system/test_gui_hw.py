"""Horn + woofer GUI data layer (G0): facts from disk, declarations from the registry, no solver.

Builds a throwaway system store in ``tmp_path`` (manifests written by the real
``provenance.write_manifest``; the solved run is the committed BL headless fixture) and drives
``gui/data_hw.py`` plus the ``/api/hw/*`` dispatch on ``gui/server.App``.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw as HW  # noqa: E402
from hornlab_search.gui.data import clean  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402

from test_clearance import write_cube  # noqa: E402

FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"

SOURCE = {"width_m": 0.32, "height_m": 0.5, "depth_m": 0.36, "wall_m": 0.018,
          "driver_diameter_m": 0.2, "driver_y_m": 0.1, "port_area_m2": 0.0028,
          "port_length_m": 0.22, "port_y_m": -0.13, "port_nfr": 0.12,
          "mesh_size_m": 0.04, "detail_size_m": 0.012}


def _case(store: Path, exp: str, name: str, payload: dict | None) -> Path:
    d = store / "system" / exp / name
    d.mkdir(parents=True)
    if payload is not None:
        provenance.write_manifest(d, payload)
    return d


def _staged_horn(store: Path, exp: str, name: str, offset_mm: float, horn_mesh: Path) -> Path:
    d = store / "system" / exp / name
    ext = write_cube(d / "bl_output" / "vented_x" / "exterior.msh", (-0.16, -0.25, -0.36), (0.16, 0.25, 0.0))
    assert ext.is_file()
    provenance.write_manifest(d, {
        "kind": "bl_stage_horn_project", "project_sha256": "ab" * 32,
        "validate": {"returncode": 0, "valid": True},
        "spec": {"source": SOURCE, "horn": {"mesh_path": str(horn_mesh), "translation_mm": [0, 0, offset_mm],
                                            "scale_factor": 1.0, "source_group": "throat",
                                            "mesh_role": "full_domain"}},
        "result": {"ok": True}})
    return d


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "repo"
    store = root / "system_runs"
    horn = write_cube(store / "system" / "ref_case" / "horn_full" / "h1" / "mesh.msh",
                      (-0.16, -0.25, 0.0), (0.16, 0.25, 0.2))
    # solved: vented-only with the committed BL headless result fixture as its run/
    solved = _case(store, "bl_motor", "20261119T000000Z-solved-1-aaaa", {
        "kind": "bl_motor_stage_project", "project_sha256": "cd" * 32,
        "spec": {"source": SOURCE}, "motor_mapping": {"driver_id": "X", "dry_mass_kg": 0.03,
                                                      "cross_checks": {"fs_error_percent": 0.4}},
        "result": {"ok": True}})
    shutil.copytree(FIXTURE_RUN, solved / "run")
    _staged_horn(store, "bl_horn", "20261118T000000Z-ok-2-bbbb", 17.0, horn)
    _staged_horn(store, "bl_horn", "20261118T000001Z-bad-3-cccc", -0.5, horn)
    _case(store, "bl_tower", "20261118T000002Z-refused-4-dddd", {
        "kind": "bl_stage_reference_project", "spec": {"source": SOURCE},
        "result": {"ok": False, "error_type": "ValueError",
                   "error": "Driver must fit inside the enclosure walls with 3 mm clearance."}})
    tampered = _case(store, "screen", "20261118T000003Z-pilot-5-eeee",
                     {"kind": "system_pilot_v0", "rows": [1, 2]})
    body = json.loads((tampered / "manifest.json").read_text(encoding="utf-8"))
    body["payload"]["kind"] = "system_pilot_v0_edited"
    (tampered / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
    reg = root / HW.REGISTRY_REL
    reg.parent.mkdir(parents=True)
    reg.write_text(
        "schema: hw_readiness_v1\nupdated: 2026-11-19\nhandoff: x.md\n"
        "cases:\n"
        "  - {key: bl_motor/20261119T000000Z-solved-1-aaaa, ref: '#4', gate: motor A,"
        " fidelity: COUPLED_VENTED_FEM_BEM_LEM, motor: real, transducer_shape: demo,"
        " evidence: FIRST_BEM_EVIDENCE.md section motor-axis A/B}\n"
        "  - {key: bl_gone/20261101T000000Z-x-9-ffff, ref: '#9', gate: deleted}\n"
        "risks:\n  - {id: R1, level: CRITICAL, status: open, wp: WP4, title: t, evidence: e}\n"
        "decisions:\n  - {id: 1, question: q, recommendation: r, status: open}\n",
        encoding="utf-8")
    HW._CACHE.clear()
    return root, store


def _by_key(cases: dict) -> dict:
    return {r["key"]: r for r in cases["cases"]}


def test_ledger_states_tokens_and_declarations(env) -> None:
    root, store = env
    data = HW.hw_cases(root, store)
    json.dumps(clean(data), allow_nan=False)
    rows = _by_key(data)
    solved = rows["bl_motor/20261119T000000Z-solved-1-aaaa"]
    assert solved["state"] == "solved" and solved["solve"]["done"] == solved["solve"]["total"] == 2
    assert solved["fidelity"] == "COUPLED_VENTED_FEM_BEM_LEM" and solved["motor"] == "real"
    assert "FIRST_BEM_EVIDENCE" in solved["evidence"]         # registry evidence pointer exposed
    assert solved["box"]["width_mm"] == 320.0 and solved["box"]["port_area_cm2"] == 28.0

    ok = rows["bl_horn/20261118T000000Z-ok-2-bbbb"]
    assert ok["state"] == "staged" and ok["clearance"]["status"] == "PASS"
    assert ok["clearance"]["source"] == "replay" and ok["clearance"]["aabb_gap_m"] == pytest.approx(0.017)
    assert ok["fidelity"] == "UNDECLARED" and ok["motor"] == "UNDECLARED"      # never inferred

    bad = rows["bl_horn/20261118T000001Z-bad-3-cccc"]
    assert bad["clearance"]["status"] == "BODY_CLEARANCE_VIOLATION"
    assert "BODY_CLEARANCE_VIOLATION" in bad["tokens"]

    refused = rows["bl_tower/20261118T000002Z-refused-4-dddd"]
    assert refused["state"] == "stage_failed"
    assert refused["tokens"] == ["STAGE_FAILED[ValueError]: Driver must fit inside the enclosure "
                                 "walls with 3 mm clearance."]

    tampered = rows["screen/20261118T000003Z-pilot-5-eeee"]
    assert tampered["integrity"].startswith("failed") and "MANIFEST_INTEGRITY_FAILED" in tampered["tokens"]

    assert [m["key"] for m in data["declared_missing"]] == ["bl_gone/20261101T000000Z-x-9-ffff"]
    # P1: the ledger KPI strip also counts recorded and empty cases (hidden rows still counted).
    assert data["counts"] == {"solved": 1, "staged": 2, "stage_failed": 1,
                              "solve_failed": 0, "recorded": 0, "empty": 0}
    assert "ref_case/horn_full" in rows and rows["ref_case/horn_full"]["family"] == "other"


@pytest.mark.parametrize("key", ["../x", "a/b/c", "bl_horn/..", "..\\x/y", "bl_horn/%2e%2e", ""])
def test_bad_keys_are_refused(env, key: str) -> None:
    root, store = env
    with pytest.raises((ValueError, FileNotFoundError)):
        HW.hw_case(root, store, key)


def test_mesh_outside_the_store_is_never_read(env, tmp_path: Path) -> None:
    root, store = env
    outside = write_cube(tmp_path / "elsewhere" / "mesh.msh", (-0.1, -0.1, 0.0), (0.1, 0.1, 0.2))
    _staged_horn(store, "bl_horn", "20261118T000009Z-out-6-gggg", 17.0, outside)
    row = _by_key(HW.hw_cases(root, store))["bl_horn/20261118T000009Z-out-6-gggg"]
    assert row["clearance"]["status"] == "NOT_CHECKED"
    detail = HW.hw_case(root, store, "bl_horn/20261118T000009Z-out-6-gggg")
    assert detail["geometry"]["horn_front"] is None and "horn_missing" in detail["geometry"]


def test_case_detail_placeholders_geometry_and_run(env) -> None:
    root, store = env
    d = HW.hw_case(root, store, "bl_horn/20261118T000000Z-ok-2-bbbb")
    json.dumps(clean(d), allow_nan=False)
    tokens = [p["token"] for p in d["placeholders"]]
    assert "IDEAL_HORN_SOURCE" in tokens and "DEMO_TRANSDUCER_SHAPE" in tokens
    assert d["run"] is None and d["observation_caption"] is None
    g = d["geometry"]
    assert g["box_bbox_mm"][1][2] == 0.0 and g["horn_bbox_mm"][0][2] == pytest.approx(17.0)
    assert len(g["horn_front"]) >= 4 and len(g["horn_side"]) >= 4

    s = HW.hw_case(root, store, "bl_motor/20261119T000000Z-solved-1-aaaa")
    tokens = [p["token"] for p in s["placeholders"]]
    assert "DEMO_MOTOR" not in tokens                       # declared real
    assert "LF_NOT_SOLVED" in tokens
    # R6 splits in two (senior review §3.2): a sampling control and a mesh-refinement line.
    assert "CONVERGENCE_SAMPLING" in tokens and "CONVERGENCE_MESH" in tokens
    assert "CONVERGENCE_UNCHECKED" not in tokens
    assert next(p["text"] for p in s["placeholders"]
                if p["token"] == "CONVERGENCE_MESH") == "Mesh refinement: not run."
    assert [e["id"] for e in s["run"]["excitations"]] == ["excitation:woofer", "excitation:horn"]
    assert s["highlights"]["motor_mapping"]["driver_id"] == "X"
    assert "not a far-field claim" in s["observation_caption"]


def test_basis_is_per_excitation_and_never_summed(env) -> None:
    root, store = env
    key = "bl_motor/20261119T000000Z-solved-1-aaaa"
    probe = HW.hw_basis(root, store, key, "observation:probe:on_axis")
    assert [e["id"] for e in probe["excitations"]] == ["excitation:woofer", "excitation:horn"]
    assert all(len(e["spl_db"]) == 2 and len(e["spl_db_points"][0]) == 2 for e in probe["excitations"])
    # Phase is unwrapped in Python; consecutive unwrapped steps cannot jump a full turn.
    for e in probe["excitations"]:
        steps = [abs(b - a) for a, b in zip(e["phase_unwrapped_deg"], e["phase_unwrapped_deg"][1:])]
        assert not steps or max(steps) < 180.0
    assert not any("sum" in k or "combined" in k for k in probe)
    polar = HW.hw_basis(root, store, key, "observation:horizontal-polar")
    for e in polar["excitations"]:
        i0 = polar["angles_deg"].index(e["normalised_to_deg"])
        assert all(row[i0] == 0.0 for row in e["rel_db"])
    with pytest.raises(ValueError):
        HW.hw_basis(root, store, key, "observation:nope")
    with pytest.raises(FileNotFoundError):
        HW.hw_basis(root, store, "bl_horn/20261118T000000Z-ok-2-bbbb", "observation:probe:on_axis")


def test_no_solver_or_boundary_lab_is_touched(env, monkeypatch: pytest.MonkeyPatch) -> None:
    from hornlab_search.system.boundarylab import run as bl_run

    def boom(*a, **k):
        raise AssertionError("GUI read path must not call Boundary Lab")
    for name in ("validate_project", "solve_project"):
        if hasattr(bl_run, name):
            monkeypatch.setattr(bl_run, name, boom)
    root, store = env
    HW.hw_cases(root, store)
    HW.hw_case(root, store, "bl_motor/20261119T000000Z-solved-1-aaaa")
    HW.hw_basis(root, store, "bl_motor/20261119T000000Z-solved-1-aaaa", "observation:probe:on_axis")
    HW.hw_readiness(root, store)
    assert "blab" not in sys.modules


def test_readiness_and_missing_registry(env) -> None:
    root, store = env
    r = HW.hw_readiness(root, store)
    json.dumps(r, allow_nan=False)                 # YAML `updated: 2026-11-19` is a date object
    assert r["updated"] == "2026-11-19"
    assert r["risks"][0]["id"] == "R1" and r["decisions"][0]["id"] == 1
    (root / HW.REGISTRY_REL).unlink()
    HW._CACHE.clear()
    data = HW.hw_cases(root, store)
    assert data["registry_error"] and all(r["fidelity"] == "UNDECLARED" for r in data["cases"])


def _write_v2(root: Path, case_files: dict[str, str]) -> None:
    """A v2 registry with one file per ``cases.d/<name>`` entry (test wiring)."""
    reg = root / HW.REGISTRY_REL
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        "schema: hw_readiness_v2\nupdated: 2026-11-20\ncase_files: [cases.d/*.yaml]\n"
        "risks:\n  - {id: R1, level: CRITICAL, status: open, wp: WP4, title: t, evidence: e}\n"
        "decisions:\n  - {id: 1, question: q, recommendation: r, status: open}\n",
        encoding="utf-8")
    cases_dir = reg.parent / "cases.d"
    cases_dir.mkdir(exist_ok=True)
    for name, body in case_files.items():
        (cases_dir / name).write_text(body, encoding="utf-8")
    HW._CACHE.clear()


def test_registry_v2_loads_cases_d_and_ignores_files_outside_it(env) -> None:
    root, store = env
    _write_v2(root, {
        "00_a.yaml": (
            "cases:\n"
            "  - {key: bl_motor/20261119T000000Z-solved-1-aaaa, ref: '#4', gate: motor A,\n"
            "     fidelity: COUPLED_VENTED_FEM_BEM_LEM, motor: real, transducer_shape: demo,\n"
            "     status: approved, approved_by: senior review 2026-11-19}\n"),
        "10_b.yaml": (
            "cases:\n"
            "  - {key: bl_horn/20261118T000000Z-ok-2-bbbb, ref: EV-1, gate: clearance control,\n"
            "     fidelity: COUPLED_VENTED_FEM_BEM_LEM, motor: demo, transducer_shape: demo,\n"
            "     status: proposed, proposed_by: evidence tool}\n"),
    })
    # A YAML beside cases.d/ (not inside it) must never be read.
    (root / HW.REGISTRY_REL).parent.joinpath("stray.yaml").write_text(
        "cases:\n  - {key: bl_horn/nope, ref: STRAY}\n", encoding="utf-8")
    data = HW.load_registry(root)
    assert data["schema"] == "hw_readiness_v2" and "error" not in data
    keys = {c["key"]: c for c in data["cases"]}
    assert keys["bl_motor/20261119T000000Z-solved-1-aaaa"]["status"] == "approved"
    assert keys["bl_horn/20261118T000000Z-ok-2-bbbb"]["status"] == "proposed"
    assert all(c["declared_in"].startswith("cases.d/") for c in data["cases"])
    assert "bl_horn/nope" not in keys
    rows = _by_key(HW.hw_cases(root, store))
    assert rows["bl_motor/20261119T000000Z-solved-1-aaaa"]["status"] == "approved"
    assert rows["bl_horn/20261118T000000Z-ok-2-bbbb"]["status"] == "proposed"


def test_registry_v2_duplicate_key_is_reported_and_never_overrides(env) -> None:
    root, store = env
    _write_v2(root, {
        "00_a.yaml": (
            "cases:\n  - {key: bl_motor/20261119T000000Z-solved-1-aaaa, ref: '#4',\n"
            "     fidelity: COUPLED_VENTED_FEM_BEM_LEM, motor: real, transducer_shape: demo}\n"),
        "10_b.yaml": (
            "cases:\n  - {key: bl_motor/20261119T000000Z-solved-1-aaaa, ref: DUP,\n"
            "     fidelity: COUPLED_VENTED_FEM_BEM_LEM, motor: demo, transducer_shape: demo}\n"),
    })
    data = HW.hw_cases(root, store)
    assert "duplicate case key(s)" in data["registry_error"]
    assert "bl_motor/20261119T000000Z-solved-1-aaaa" in data["registry_error"]
    row = _by_key(data)["bl_motor/20261119T000000Z-solved-1-aaaa"]
    # Ambiguous declarations are dropped, not resolved last-wins: the case shows UNDECLARED.
    assert row["declared"] is False and row["fidelity"] == "UNDECLARED"


def test_server_dispatch(env) -> None:
    from hornlab_search.gui.server import App

    root, store = env
    app = App(root, system_store=store)
    assert app.get("/api/hw/cases", {})["counts"]["solved"] == 1
    assert app.get("/api/hw/case/bl_motor/20261119T000000Z-solved-1-aaaa", {})["row"]["state"] == "solved"
    b = app.get("/api/hw/basis/bl_motor/20261119T000000Z-solved-1-aaaa",
                {"domain": ["observation:probe:on_axis"]})
    assert len(b["excitations"]) == 2
    assert app.get("/api/hw/readiness", {})["decisions"]
    # P6 backend routes for the stage/solve dialogs (no solver, no write on GET).
    options = app.get("/api/hw/stage-options", {})
    assert options["horn_meshes"] and "clearance_m" not in options
    presets = app.get("/api/hw/solve-presets", {})
    assert [p["id"] for p in presets["presets"]] == ["smoke3", "wide25", "lowband12"]
    auth = app.get("/api/hw/authorization", {})
    assert auth["allowed"] is False and "decision 6" in auth["reason"]
    # P7: per-channel filtered preview; no summed field.
    dsp = app.post("/api/hw/dsp-preview", {"case": "bl_motor/20261119T000000Z-solved-1-aaaa"})
    assert dsp["ok"] is True and len(dsp["channels"]) == 2
    assert not any("sum" in k.lower() or "combined" in k.lower() for k in dsp)
    # P2: screens list/detail and the pure panel-fit recompute are wired.
    screens = app.get("/api/hw/screens", {})
    assert screens["studies"] == [] and "store" in screens          # fixture store has no studies
    with pytest.raises(FileNotFoundError):
        app.get("/api/hw/screen/0123456789abcdef", {})
    fit = app.post("/api/hw/panel-fit", {"height_mm": 371.2, "port_throat_area_cm2": 170.0,
                                         "net_volume_l": 115.0, "wall_mm": 18.0})
    assert fit["feasible"] is False and fit["reason"].startswith("BL_PANEL_FIT_")
    assert fit["required_m"] > fit["available_m"]
    with pytest.raises(ValueError):
        app.post("/api/hw/panel-fit", {"height_mm": 9999, "port_throat_area_cm2": 170.0,
                                       "net_volume_l": 115.0, "wall_mm": 18.0})
    # P3: both mesh parts are wired (the staged fixture has an exterior and a horn mesh).
    box = app.get("/api/hw/mesh/bl_horn/20261118T000000Z-ok-2-bbbb", {"part": ["box"]})
    horn = app.get("/api/hw/mesh/bl_horn/20261118T000000Z-ok-2-bbbb", {"part": ["horn"]})
    assert box["triangle_count"] > 0 and box["units"] == "mm"
    assert horn["triangle_count"] > 0 and horn["bbox"][0][2] == pytest.approx(17.0)
    with pytest.raises(ValueError):
        app.get("/api/hw/mesh/bl_horn/20261118T000000Z-ok-2-bbbb", {"part": ["walls"]})
    # P4: A/B compare is wired; a case compared with itself is comparable and never summed.
    solved = "bl_motor/20261119T000000Z-solved-1-aaaa"
    cmp = app.get("/api/hw/compare", {"a": [solved], "b": [solved]})
    assert cmp["ok"] is True and "bands" in cmp
    assert not any("sum" in k.lower() or "combined" in k.lower() for k in cmp)
    mat = app.get("/api/hw/compare-matrix", {"keys": [solved]})
    assert len(mat["cells"]) == 1 and mat["edges"] == []
    with pytest.raises(FileNotFoundError):
        app.get("/api/hw/compare", {"a": [solved], "b": ["bl_horn/20261118T000000Z-ok-2-bbbb"]})
    with pytest.raises(FileNotFoundError):
        app.get("/api/hw/nope", {})


def test_new_system_dispatch(env, tmp_path: Path) -> None:
    """P5: asset/driver inventory, spec validate/save and the hw-screen preview prefix."""
    from hornlab_search.gui.server import App

    root, store = env
    repo = Path(__file__).resolve().parents[2]
    shutil.copytree(repo / "examples" / "systems", root / "examples" / "systems")
    app = App(root, system_store=store)

    assert app.get("/api/hw/assets", {})["assets"] is not None
    assert any(d["driver_id"] for d in app.get("/api/hw/drivers", {})["drivers"])
    defaults = app.get("/api/hw/spec-defaults", {})
    assert defaults["source"].endswith("two_way_80x50_700_research.yaml")
    spec = defaults["spec"]

    assert app.post("/api/hw/spec/validate", {"spec": spec})["ok"] is True
    bad = app.post("/api/hw/spec/validate", {"spec": {"not_a_key": 1}})
    assert bad["ok"] is False and bad["errors"]

    saved = app.post("/api/hw/spec/save", {"name": "tmp_user_spec", "spec": spec})
    assert isinstance(saved, str) and saved.endswith("examples/systems/user/tmp_user_spec.yaml")
    path = root / saved
    assert path.is_file() and b"\r\n" not in path.read_bytes()
    with pytest.raises(ValueError):
        app.post("/api/hw/spec/save", {"name": "tmp_user_spec", "spec": spec})
    assert app.post("/api/hw/spec/save", {"name": "tmp_user_spec", "spec": spec,
                                          "replace": True}) == saved

    prev = app.post("/api/preview", {"kind": "hw-screen", "args": {
        "spec": saved, "asset_id": "0123456789abcdef",
        "drivers": ["faitalpro_12pr300"]}})
    assert prev["command"].startswith("python tools/system/gui_system_job.py screen")
    assert prev["gpu"] is False and "beat_cpu" not in prev["command"]
    with pytest.raises(ValueError):
        app.post("/api/hw/spec/save", {"name": "../escape", "spec": spec})


def test_overview_next_step_is_computed_from_disk(env) -> None:
    from hornlab_search.gui.server import App

    root, store = env
    assert HW.overview_next_step([], {})["id"] == "new"
    study = {"study_id": "0123456789abcdef", "counts": {"shortlist_rows": 3}}
    assert HW.overview_next_step([study], {"staged": 0, "solved": 0})["id"] == "stage"
    assert HW.overview_next_step([study], {"staged": 0, "solved": 2})["id"] == "compare"
    assert HW.overview_next_step([study], {"staged": 0, "solved": 1})["id"] == "read"
    assert HW.overview_next_step([study], {"staged": 7, "solved": 0})["id"] == "solve"
    assert HW.overview_next_step([study], {"staged": 0, "solved": 0,
                                           "shortlist_rows": 0})["id"] == "stage"
    # An in-progress R3 audit outranks "compare": the next scientific step is not a GUI action.
    r3 = [{"id": "R3", "status": "in_progress",
           "evidence": "README#lf-on-axis (LF solved; bassbox model-difference audit open)"}]
    nxt = HW.overview_next_step([study], {"staged": 0, "solved": 2}, r3)
    assert nxt["id"] == "r3_audit" and nxt["href"] == "#/hw/readiness"
    assert "bassbox" in nxt["why"]

    app = App(root, system_store=store)
    ov = app.get("/api/hw/overview", {})
    assert ov["kpis"]["solved"] == 1 and ov["next_step"]["id"] == "read"
    assert len(ov["recent_cases"]) <= 5
    assert ov["readiness"]["risks_total"] == 1 and ov["readiness"]["open_decisions"][0]["id"] == 1


def test_committed_registry_parses_and_names_real_cases() -> None:
    repo = Path(__file__).resolve().parents[2]
    HW._CACHE.clear()
    reg = HW.load_registry(repo)
    assert reg.get("schema") == "hw_readiness_v2" and "error" not in reg
    ids = [r["id"] for r in reg["risks"]]
    assert ids == [f"R{i}" for i in range(1, 18)]
    allowed = {"SCREEN_MAGNITUDE", "SCREEN_COMPLEX_APPROX", "INSTALLED_EXTERIOR_BEM",
               "COUPLED_VENTED_FEM_BEM_LEM", "MEASURED_VALIDATED"}
    for c in reg["cases"]:
        assert len(c["key"].split("/")) == 2
        assert c.get("fidelity") is None or c["fidelity"] in allowed
        assert c.get("motor") in ("real", "demo") and c.get("transducer_shape") in ("real", "demo")
        assert c.get("status") in ("approved", "proposed")
        assert c.get("declared_in", "").startswith("cases.d/")
    # The 2026-11-19 handoff entries stay approved; the evidence-queue entries stay proposed
    # until the owner answers gate H.
    assert sum(1 for c in reg["cases"] if c["status"] == "approved") == 9
    assert sum(1 for c in reg["cases"] if c["status"] == "proposed") == 16
    assert all(c.get("approved_by") for c in reg["cases"] if c["status"] == "approved")
    assert all(c.get("proposed_by") for c in reg["cases"] if c["status"] == "proposed")
