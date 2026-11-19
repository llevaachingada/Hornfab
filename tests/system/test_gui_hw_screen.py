"""Horn + woofer GUI — P2 screen store: verbatim payloads, grouped replays, panel-fit numbers.

Two layers:

* **live store** — the parent's recorded screens (``system_runs/woofer_seed*``), skipped with a
  reason when the gitignored store is not on this machine (mirrors
  ``test_clearance.py::test_real_staged_cases_replay``).  These tests prove the GUI rows are the
  recorded JSON rows, field for field, and that the KPI counters agree with the study's own.
* **synthetic store** — a throwaway ``tmp_path`` store for the refusals: invalid study ids,
  allow-list containment, oversized files, replay grouping and the no-solver guarantee.

No solver, no GPU, no Boundary Lab: ``data_hw_screen`` is a read-only JSON/GUI layer.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from hornlab_search.gui import data_hw_screen as G
from hornlab_search.system import contracts as C
from hornlab_search.system import woofer_seed as W

REPO = Path(__file__).resolve().parents[2]
LIVE_STUDY = "27616eedee09009f"          # the BL-panel-fit screen (P2 acceptance)
FIT_STUDY = "65f6db3e8c8e8f86"           # the earlier screen, no bl_panel_fit_rejected counter
LIVE_DIRS = ("woofer_seed_stage5_blfit", "woofer_seed_stage5")


# --------------------------------------------------------------------------- live store helper


def _live_store() -> Path:
    """The recorded system store, from ``$HORNLAB_SYSTEM_STORE``, the repo, or the parent tree."""
    candidates: list[Path] = []
    env = os.environ.get("HORNLAB_SYSTEM_STORE")
    if env:
        candidates.append(Path(env))
    candidates += [REPO / "system_runs",
                   REPO.parent / "hornlab-woofer-system-wt" / "system_runs"]
    for store in candidates:
        if any((store / name / G.STUDY_FILE).is_file() for name in LIVE_DIRS):
            return store
    pytest.skip(f"gitignored system store / {LIVE_STUDY} not on disk: {[str(c) for c in candidates]}")


def _study_json(store: Path, sid: str) -> tuple[dict, Path]:
    detail = G.hw_screen(REPO, store, sid)
    return json.loads((store / detail["dir"] / G.STUDY_FILE).read_text(encoding="utf-8")), \
        store / detail["dir"]


# --------------------------------------------------------------------------- live: verbatim rows


def test_live_shortlist_and_kept_rows_are_the_recorded_json() -> None:
    store = _live_store()
    recorded, _ = _study_json(store, LIVE_STUDY)
    detail = G.hw_screen(REPO, store, LIVE_STUDY)

    assert len(detail["shortlist"]) == len(recorded["shortlist"]) == detail["counts"]["shortlist_rows"]
    assert detail["shortlist"] == recorded["shortlist"]
    assert detail["kept_rows"] == recorded["kept_rows"]
    # A sampled row, field by field: the GUI may not reshape a single value.
    row, truth = detail["shortlist"][0], recorded["shortlist"][0]
    for field in ("candidate_id", "driver_id", "driver_name", "box", "xo_hz", "xo_band_hz",
                  "placement", "match", "numeric_axes", "feasibility", "lf", "status",
                  "shortlist_reason"):
        assert row[field] == truth[field], field
    # The payload sections the detail tab shows are echoed, not recomputed.
    for field in ("envelope", "metric_spec", "catalog", "xo_screens", "claim", "schema"):
        assert detail[field] == recorded[field], field


def test_live_kpis_pareto_grouping_and_ledger() -> None:
    store = _live_store()
    recorded, _ = _study_json(store, LIVE_STUDY)
    detail = G.hw_screen(REPO, store, LIVE_STUDY)

    # KPI strip: the study's own counters, with a null (plus counts_missing) for absent ones.
    assert detail["counts"] == recorded["counts"]
    assert detail["counts_missing"] == []
    assert detail["counts"]["bl_panel_fit_rejected"] == 11

    # Pareto front recomputed in Python from kept_rows + axis_directions.
    assert detail["axis_directions"] == recorded["kept_rows"][0]["axis_directions"]
    assert detail["numeric_axes"] == list(W.SEED_AXIS_DIRECTIONS)
    assert len(detail["pareto_ids"]) == detail["counts"]["pareto_front_rows"] == 9
    kept_ids = {row["candidate_id"] for row in detail["kept_rows"]}
    assert set(detail["pareto_ids"]) <= kept_ids
    assert len(detail["pareto_ids"]) == len(set(detail["pareto_ids"]))

    # Rejected ledger: flat rows grouped by stage, verbatim, nothing dropped.
    ledger = recorded["rejected_ledger"]
    assert sum(group["count"] for group in detail["rejected"]) == len(ledger)
    assert all(group["count"] == len(group["rows"]) for group in detail["rejected"])
    by_stage = {group["stage"]: group for group in detail["rejected"]}
    assert by_stage["bl_panel_fit"]["count"] == detail["counts"]["bl_panel_fit_rejected"]
    assert all(row in ledger for group in detail["rejected"] for row in group["rows"])


def test_live_older_screen_reports_the_missing_counter() -> None:
    store = _live_store()
    if not (store / "woofer_seed_stage5" / G.STUDY_FILE).is_file():
        pytest.skip(f"older screen {FIT_STUDY} not staged next to the live store")
    detail = G.hw_screen(REPO, store, FIT_STUDY)
    assert detail["counts_missing"] == ["bl_panel_fit_rejected"]
    assert detail["counts"]["bl_panel_fit_rejected"] is None


def test_live_replays_group_and_are_byte_identical() -> None:
    store = _live_store()
    screens = G.hw_screens(REPO, store)
    assert screens["errors"] == []
    grouped = {row["study_id"]: row for row in screens["studies"]}
    assert LIVE_STUDY in grouped
    row = grouped[LIVE_STUDY]
    if not (store / "woofer_seed_stage5_blfit_replay" / G.STUDY_FILE).is_file():
        pytest.skip("the byte-identical replay dir is not staged next to the live store")
    assert row["replay_count"] == 2
    assert row["byte_identical"] is True
    assert len(row["paths"]) == 2 and len(set(row["paths"])) == 2
    assert row["dir"] == row["paths"][0]
    detail = G.hw_screen(REPO, store, LIVE_STUDY)
    assert detail["replay"] == {"paths": row["paths"], "count": 2, "byte_identical": True}


# --------------------------------------------------------------------------- panel fit


def _recorded_case_box(**overrides) -> C.BoxPoint:
    """The recorded 115 L / 371.2 mm / 170 cm^2 cell (same source as test_woofer_seed)."""
    import math

    r_eq = math.sqrt(170.0 * 1e-4 / math.pi)
    neck_m = 0.15488  # BL source port_length_m in the recorded case
    values = {
        "kind": "vented", "external_width_mm": 371.2, "external_height_mm": 371.2,
        "external_depth_mm": 1080.690776151898, "net_volume_l": 115.0, "wall_mm": 18.0,
        "port_type": "round_flared", "port_throat_area_cm2": 170.0, "port_nfr": 0.0,
        "requested_tuning_hz": 49.72,
        "derived_effective_port_length_m": neck_m + 2.0 * 0.85 * r_eq,
        "derived_tuning_hz": 49.72, "fits": {},
    }
    values.update(overrides)
    return C.BoxPoint(**values)


def test_real_12pr300_dims_reproduce_the_acceptance_numbers() -> None:
    # Sd-derived moving diameter of the FaitalPRO 12PR300 on the recorded 371.2 mm front.
    detail = G.panel_fit({
        "height_mm": 371.2, "port_throat_area_cm2": 45.0, "net_volume_l": 115.0,
        "wall_mm": 18.0, "driver_moving_diameter_m": 0.2605,
    })
    assert detail["required_m"] == pytest.approx(0.1821, abs=5e-5)
    assert detail["available_m"] == pytest.approx(0.1501, abs=5e-5)
    assert detail["feasible"] is False
    assert detail["reason"] == W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    # The same numbers behind the boolean entry point, from the recorded box point.
    sep = W.bl_panel_fit_separation(_recorded_case_box(port_throat_area_cm2=45.0),
                                    driver_moving_diameter_m=0.2605)
    assert sep["required_m"] == pytest.approx(0.1821, abs=5e-5)
    assert sep["available_m"] == pytest.approx(0.1501, abs=5e-5)
    assert (sep["feasible"], sep["reason"]) == (False, W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION)


def test_demo_170cm2_cell_reproduces_the_root_cause_refusal() -> None:
    # BL itself refused the staged cell with "Driver must fit inside the enclosure walls with
    # 3 mm clearance." -> its literal per-component check is BL_PANEL_FIT_DRIVER_WALL (see
    # test_woofer_seed.py::test_recorded_bl_refusal_case_is_rejected_by_panel_fit).  This screen
    # path deliberately reports the *root cause* first -- the 371.2 mm front cannot separate a
    # 200 mm demo driver from a 170 cm^2 port at any legal y -- so the GUI's demo mode returns
    # BL_PANEL_FIT_DRIVER_PORT_SEPARATION.  Both tokens are the recorded refusal family; the
    # difference is ordering, documented in woofer_seed.bl_panel_fit_feasible's docstring.
    demo = G.panel_fit({
        "height_mm": 371.2, "port_throat_area_cm2": 170.0, "net_volume_l": 115.0, "wall_mm": 18.0,
    })
    assert demo["feasible"] is False
    assert demo["reason"] == W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    assert demo["inputs"]["driver_moving_diameter_m"] == W.BL_DEMO_DRIVER_MOVING_DIAMETER_M
    assert demo["inputs"]["width_mm"] == demo["inputs"]["depth_mm"] == 371.2
    # The screen wrapper's own ledger row for the recorded cell carries the same token.
    assert W.bl_panel_fit_feasible(_recorded_case_box())[1] == \
        W.BL_PANEL_FIT_DRIVER_PORT_SEPARATION


def test_panel_fit_is_pure_and_deterministic() -> None:
    payload = {"height_mm": 420.0, "port_throat_area_cm2": 60.0, "net_volume_l": 90.0,
               "wall_mm": 18.0}
    first = G.panel_fit(payload)
    for _ in range(3):
        assert G.panel_fit(payload) == first
    assert payload == {"height_mm": 420.0, "port_throat_area_cm2": 60.0, "net_volume_l": 90.0,
                       "wall_mm": 18.0}                        # the input is not mutated
    assert set(first) == {"feasible", "reason", "required_m", "available_m", "driver_y_m",
                          "port_y_m", "port_length_checked", "inputs"}


@pytest.mark.parametrize("payload, field", [
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 18.0, "banana": 1.0}, "banana"),
    ({"height_mm": 30300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 18.0}, "height_mm"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 2.0, "net_volume_l": 90.0,
      "wall_mm": 18.0}, "port_throat_area_cm2"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 900.0,
      "wall_mm": 18.0}, "net_volume_l"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 2.0}, "wall_mm"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 18.0, "driver_moving_diameter_m": 0.9}, "driver_moving_diameter_m"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 18.0, "clearance_m": 0.0}, "clearance_m"),
    ({"height_mm": 300.0, "port_throat_area_cm2": 45.0, "net_volume_l": 90.0,
      "wall_mm": 18.0, "width_mm": "wide"}, "width_mm"),
    ({"port_throat_area_cm2": 45.0, "net_volume_l": 90.0, "wall_mm": 18.0}, "height_mm"),
])
def test_panel_fit_refusals_name_the_field(payload: dict, field: str) -> None:
    with pytest.raises(ValueError) as exc:
        G.panel_fit(payload)
    assert field in str(exc.value)


def test_panel_fit_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError):
        G.panel_fit([("height_mm", 371.2)])


# --------------------------------------------------------------------------- synthetic store


def _payload(sid: str, **overrides) -> dict:
    payload = {
        "schema": W.SEED_SCHEMA,
        "study_id": sid,
        "system_objective_version": 1,
        "asset": {"asset_id": "0062fb59fbf63eae", "brief_id": "lecleach_rollback_1in_v6",
                  "design_hash": "9e02db06ecc3", "family": "FREEFORM",
                  "quality": "MAGNITUDE_ONLY", "freq_lo_hz": 500.0, "freq_hi_hz": 5500.0,
                  "n_freqs": 12},
        "envelope": {"width_mm": 240.0, "height_mm": 240.0, "depth_mm": 143.0},
        "catalog": [{"driver_id": "faitalpro_12pr300", "name": "FaitalPRO 12PR300"}],
        "catalog_rejected": [],
        "fingerprints": {},
        "metric_spec": {"half_octaves": 0.5, "planes": "H and V separate"},
        # Every counter the KPI strip reads except the pre-R16 ``bl_panel_fit_rejected``.
        "counts": {**{k: 0 for k in G._COUNT_KEYS if k != "bl_panel_fit_rejected"},
                   "drivers_loaded": 1, "boxes_considered": 2, "candidates_kept": 2,
                   "pareto_front_rows": 1, "shortlist_rows": 1},
        "xo_screens": {"faitalpro_12pr300": {"hypothesis_centers_hz": [700.0]}},
        "kept_rows": [
            {"candidate_id": "0000000000000001", "driver_id": "faitalpro_12pr300",
             "axis_directions": dict(W.SEED_AXIS_DIRECTIONS),
             "numeric_axes": {"match_error_h_db2": 0.4, "match_error_v_db2": 0.5,
                              "lf_f3_hz": 45.0, "port_velocity_ratio": 0.5,
                              "excursion_margin_db": 6.0, "cabinet_footprint_m2": 0.4,
                              "mounting_distance_mm": 300.0},
             "feasibility": {"port_fits": True, "wall": True, "driver_clearance": True,
                             "f3_gate": True, "bl_panel_fit": True, "placement_legal": True,
                             "xo_data": True}},
            {"candidate_id": "0000000000000002", "driver_id": "faitalpro_12pr300",
             "axis_directions": dict(W.SEED_AXIS_DIRECTIONS),
             "numeric_axes": {"match_error_h_db2": 0.9, "match_error_v_db2": 0.9,
                              "lf_f3_hz": 55.0, "port_velocity_ratio": 0.7,
                              "excursion_margin_db": 3.0, "cabinet_footprint_m2": 0.6,
                              "mounting_distance_mm": 340.0},
             "feasibility": {"port_fits": True, "wall": True, "driver_clearance": True,
                             "f3_gate": True, "bl_panel_fit": True, "placement_legal": True,
                             "xo_data": True}},
        ],
        "shortlist": [],
        "rejected_ledger": [{"stage": "box_gate", "driver_id": "faitalpro_12pr300",
                             "reasons": ["f3 60 Hz > target 55 Hz"]}],
        "claim": "heuristic fixed-horn screen; no scalar winner; not a validated ranking.",
    }
    payload.update(overrides)
    payload["shortlist"] = [dict(payload["kept_rows"][0], shortlist_reason="pareto_fill")]
    return payload


def _write_study(store: Path, name: str, payload: dict) -> Path:
    d = store / name
    d.mkdir(parents=True, exist_ok=True)
    (d / G.STUDY_FILE).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return d


@pytest.fixture()
def synthetic(tmp_path: Path) -> Path:
    store = tmp_path / "system_runs"
    _write_study(store, "woofer_seed_a", _payload("0123456789abcdef"))
    _write_study(store, "woofer_seed_b", _payload("0123456789abcdef"))
    _write_study(store, "screens/0123456789abcdef_alt", _payload("fedcba9876543210"))
    _write_study(store, "woofer_seed_bad", _payload("not-a-study-id"))
    _write_study(store, "elsewhere", _payload("1111111111111111"))   # outside the allow-list
    G._CACHE.clear()
    return store


def test_allow_list_and_replay_grouping(synthetic: Path) -> None:
    out = G.hw_screens(REPO, synthetic)
    rows = {row["study_id"]: row for row in out["studies"]}
    assert set(rows) == {"0123456789abcdef", "fedcba9876543210"}
    assert rows["0123456789abcdef"]["paths"] == ["woofer_seed_a", "woofer_seed_b"]
    assert rows["0123456789abcdef"]["replay_count"] == 2
    assert rows["0123456789abcdef"]["byte_identical"] is True
    assert rows["fedcba9876543210"]["dir"] == "screens/0123456789abcdef_alt"
    assert rows["fedcba9876543210"]["replay_count"] == 1
    # The invalid id and a file under a non-allow-listed dir are never silently skipped.
    assert [e["path"] for e in out["errors"]] == ["woofer_seed_bad"]
    assert "study_id" in out["errors"][0]["error"]
    assert all("elsewhere" not in row["paths"] for row in out["studies"])

    detail = G.hw_screen(REPO, synthetic, "0123456789abcdef")
    assert detail["replay"] == {"paths": ["woofer_seed_a", "woofer_seed_b"], "count": 2,
                                "byte_identical": True}
    # Recomputed Pareto front: row 2 is dominated by row 1 on every axis that matters.
    assert detail["pareto_ids"] == ["0000000000000001"]
    assert detail["counts"]["bl_panel_fit_rejected"] is None
    assert detail["counts_missing"] == ["bl_panel_fit_rejected"]
    assert [g["stage"] for g in detail["rejected"]] == ["box_gate"]


def test_a_diverged_replay_is_not_byte_identical(synthetic: Path) -> None:
    diverged = _payload("0123456789abcdef", claim="edited copy")
    _write_study(synthetic, "woofer_seed_c", diverged)
    G._CACHE.clear()
    row = next(r for r in G.hw_screens(REPO, synthetic)["studies"]
               if r["study_id"] == "0123456789abcdef")
    assert row["replay_count"] == 3
    assert row["byte_identical"] is False
    detail = G.hw_screen(REPO, synthetic, "0123456789abcdef")
    assert detail["replay"]["count"] == 3 and detail["replay"]["byte_identical"] is False
    assert detail["sha256"] == row["sha256"]


@pytest.mark.parametrize("study", ["../woofer_seed_a", "../../0123456789abcdef",
                                   "0123456789ABCDEF", "0123456789abcde", "", "0123456789abcdef0",
                                   "woofer_seed_stage5_blfit"])
def test_bad_study_ids_are_refused(synthetic: Path, study: str) -> None:
    with pytest.raises(ValueError):
        G.hw_screen(REPO, synthetic, study)


def test_unknown_study_id_is_not_found(synthetic: Path) -> None:
    with pytest.raises(FileNotFoundError):
        G.hw_screen(REPO, synthetic, "0000000000000000")


def test_oversized_study_file_is_refused_unread(synthetic: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(G, "SCREEN_MAX_BYTES", 64)
    G._CACHE.clear()
    out = G.hw_screens(REPO, synthetic)
    errors = {e["path"]: e["error"] for e in out["errors"]}
    assert "byte limit" in errors["woofer_seed_a"]
    assert out["studies"] == [] or all("woofer_seed_a" not in s["paths"] for s in out["studies"])


def test_empty_store_is_an_empty_list(tmp_path: Path) -> None:
    out = G.hw_screens(REPO, tmp_path / "missing")
    assert out["studies"] == [] and out["errors"] == []


# --------------------------------------------------------------------------- no solver / no BL


def _boom(*_args, **_kwargs):
    raise AssertionError("the GUI screen read path must not call a Boundary Lab entry point")


def test_no_solver_or_boundary_lab_is_touched(synthetic: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    for name in ("stage", "run", "reference"):
        try:
            module = importlib.import_module(f"hornlab_search.system.boundarylab.{name}")
        except ImportError:                     # `reference` does not exist in this tree
            continue
        seen.append(name)
        for attr in dir(module):
            if attr.startswith("_"):
                continue
            obj = getattr(module, attr)
            if callable(obj) and getattr(obj, "__module__", None) == module.__name__:
                monkeypatch.setattr(module, attr, _boom)
    assert "stage" in seen and "run" in seen

    listing = G.hw_screens(REPO, synthetic)
    assert listing["studies"]
    G.hw_screen(REPO, synthetic, "0123456789abcdef")
    G.panel_fit({"height_mm": 371.2, "port_throat_area_cm2": 170.0, "net_volume_l": 115.0,
                 "wall_mm": 18.0})
    assert "blab" not in sys.modules


def test_module_has_no_boundarylab_import() -> None:
    source = Path(G.__file__).read_text(encoding="utf-8")
    assert "import boundarylab" not in source
    assert "import hornlab_search.system.boundarylab" not in source
    assert "blab" not in source
