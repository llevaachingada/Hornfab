"""Offline tests for :mod:`hornlab_search.system.horn_full_domain`.

The pure recipe/QA helpers run everywhere.  The one live test rebuilds the canonical
reference asset through the EXISTING mesher on the CPU; it is gated by the repo's shared
``requires_mesher`` mark (``tests/conftest.py``), the same convention as the other
real-mesher tests.  No GPU is used, and no solve is run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import requires_mesher  # noqa: E402
from hornlab_search.design.generators import grid as grid_gen  # noqa: E402
from hornlab_search.system import horn_full_domain as H  # noqa: E402
from hornlab_search.types import Design  # noqa: E402


# ------------------------------------------------------------------ full recipe


def test_full_grid_params_promotes_the_span_and_keeps_every_geometry_parameter() -> None:
    params = {
        "grid": {
            "rows": {"type": "lecleach"},
            "n_phi": 15,
            "n_s": 32,
            "wall_thickness_mm": 3.0,
            "knobs": {"g_T": 0.755889079, "g_fc_hz": 706.486777282},
        }
    }
    full = H.full_grid_params(params)

    # input is never mutated
    assert "span" not in params["grid"] and params["grid"]["n_phi"] == 15

    block = full["grid"]
    assert block["span"] == "full"
    assert block["n_phi"] >= grid_gen.MIN_PHI_FULL
    assert block["n_phi"] % 8 == 0, "needs 45/90/180 deg rows for exact x/y parity"
    # geometry and wall sampling untouched
    assert block["n_s"] == 32
    assert block["wall_thickness_mm"] == 3.0
    assert block["rows"] == {"type": "lecleach"}
    assert block["knobs"] == params["grid"]["knobs"]


def test_full_grid_params_refuses_a_non_rows_grid() -> None:
    with pytest.raises(H.HornFullDomainError, match="rows"):
        H.full_grid_params({"grid": {"profile_h": {"a": 1}, "n_phi": 15, "n_s": 32}})


# ------------------------------------------------------------------ bbox parity


def test_mirrored_bbox_deltas_are_zero_for_a_mirrored_horn() -> None:
    quarter = (0.0, 0.0, -0.003, 0.1166727878710462, 0.1166727878710462,
               0.1398739567509541)
    full = (-0.1166727878710462, -0.1166727878710462, -0.003,
            0.1166727878710462, 0.1166727878710462, 0.1398739567509541)
    deltas = H.mirrored_bbox_deltas(quarter, full)
    assert deltas["max"] == pytest.approx(0.0, abs=1e-15)
    for key in ("x_minus", "x_plus", "y_minus", "y_plus", "z_min", "z_max"):
        assert deltas[key] == pytest.approx(0.0, abs=1e-15)


def test_mirrored_bbox_deltas_detect_a_shift_or_a_depth_change() -> None:
    quarter = (0.0, 0.0, -0.003, 0.1166, 0.1166, 0.1398)
    shifted = (-0.1166 + 0.001, -0.1166, -0.003, 0.1166, 0.1166, 0.1398)
    assert H.mirrored_bbox_deltas(quarter, shifted)["max"] == pytest.approx(0.001)
    deeper = (-0.1166, -0.1166, -0.003, 0.1166, 0.1166, 0.1498)
    assert H.mirrored_bbox_deltas(quarter, deeper)["z_max"] == pytest.approx(0.01)


# ------------------------------------------------------------------ QA closure


def _qa(**over):
    base = dict(
        path="mesh.msh", n_points=10, n_triangles=10, closed=True,
        orientation_consistent=True, free_edges=0, free_edges_on_symmetry_planes=0,
        symmetric_patch=False, full_open_holes=0, duplicate_points=0,
        bbox_min_m=(-0.1166727878710462, -0.1166727878710462, -0.003),
        bbox_max_m=(0.1166727878710462, 0.1166727878710462, 0.1398739567509541),
        groups=("SD1D1001", "SD1G0"))
    base.update(over)
    return SimpleNamespace(**base)


def test_validate_full_domain_qa_accepts_a_closed_mirrored_horn() -> None:
    quarter = (0.0, 0.0, -0.003, 0.1166727878710462, 0.1166727878710462,
               0.1398739567509541)
    H.validate_full_domain_qa(_qa(), quarter)  # does not raise


def test_validate_full_domain_qa_rejects_the_saved_quarter_patch() -> None:
    quarter = (0.0, 0.0, -0.003, 0.1166727878710462, 0.1166727878710462,
               0.1398739567509541)
    patch = _qa(closed=False, free_edges=162, free_edges_on_symmetry_planes=162,
                symmetric_patch=True,
                bbox_min_m=(0.0, 0.0, -0.003),
                bbox_max_m=(0.1166727878710462, 0.1166727878710462, 0.1398739567509541))
    with pytest.raises(H.FullDomainQAError, match="not closed|free edges|symmetry patch"):
        H.validate_full_domain_qa(patch, quarter)


def test_validate_full_domain_qa_enforces_the_metre_scale_guard() -> None:
    quarter = (0.0, 0.0, 0.0, 0.02, 0.02, 0.02)
    tiny = _qa(bbox_min_m=(-0.02, -0.02, 0.0), bbox_max_m=(0.02, 0.02, 0.02))
    with pytest.raises(H.FullDomainQAError, match="scale guard"):
        H.validate_full_domain_qa(tiny, quarter)


# ------------------------------------------------------------------ discovery


def _write_saved_design(tmp_path: Path) -> tuple[Path, str]:
    run = tmp_path / "runs" / "20260101T000000Z-test"
    params = {"grid": {"rows": {"type": "lecleach"}, "n_phi": 15, "n_s": 32,
                       "wall_thickness_mm": 3.0, "knobs": {"g_T": 0.7}}}
    design_hash = Design(family="FREEFORM", params=params).hash()
    design_dir = run / "designs" / design_hash
    design_dir.mkdir(parents=True)
    (design_dir / "design.json").write_text(json.dumps({
        "design_hash": design_hash,
        "family": "FREEFORM",
        "generator": {"brief": "test_brief"},
        "params": params,
    }), encoding="utf-8")
    (design_dir / "status.json").write_text("{}", encoding="utf-8")
    (run / "config.yaml").write_text("name: test\n", encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"lib_shas": {"hornlab_mesher": "abc"}}),
                                 encoding="utf-8")
    return run, design_hash


def test_discover_asset_reads_the_saved_recipe_and_checks_its_hash(tmp_path: Path) -> None:
    run, design_hash = _write_saved_design(tmp_path)
    ref = H.discover_asset(tmp_path / "runs", run.name, design_hash)
    assert ref.design_hash == design_hash
    assert ref.family == "FREEFORM"
    assert ref.brief == "test_brief"
    assert ref.design.params["grid"]["n_phi"] == 15


def test_discover_asset_refuses_a_recipe_that_changed_under_its_hash(tmp_path: Path) -> None:
    run, design_hash = _write_saved_design(tmp_path)
    design_json = run / "designs" / design_hash / "design.json"
    payload = json.loads(design_json.read_text(encoding="utf-8"))
    payload["design_hash"] = "000000000000"
    design_json.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(H.ProvenanceError, match="does not hash"):
        H.discover_asset(tmp_path / "runs", run.name, design_hash)


# ------------------------------------------------------------------ live rebuild


@requires_mesher
def test_full_domain_rebuild_closes_the_reference_case(tmp_path: Path) -> None:
    """Rebuild the canonical quarter asset at ``quadrants='1234'`` and QA the result.

    CPU gmsh only (no GPU, no solve).  The canonical run tree is read-only; if this
    machine does not carry it, the test skips with the suite's existing asset wording.
    """
    design_dir = (H.DEFAULT_RUNS_ROOT / H.DEFAULT_RUN_NAME / "designs"
                  / H.DEFAULT_DESIGN_HASH)
    if not (design_dir / "design.json").is_file():
        pytest.skip("canonical run mesh not present")

    ref = H.discover_asset()
    report = H.build_full_domain_mesh(ref, out_root=tmp_path, case_tag="ref_case")

    # provenance gate: the saved quarter regenerates from its own recipe
    gate = report.provenance_gate
    assert gate.ok is True
    assert gate.max_abs_bbox_delta_m <= gate.tol_m
    assert gate.area_rel_delta <= H.AREA_PARITY_REL
    assert gate.rebuilt_triangles == gate.stored_triangles

    # full-domain closure
    qa = report.qa
    assert qa.closed is True
    assert qa.orientation_consistent is True
    assert qa.free_edges == 0
    assert qa.full_open_holes == 0
    assert qa.duplicate_points == 0
    assert qa.symmetric_patch is False
    assert list(qa.groups) == ["SD1D1001", "SD1G0"]

    # mirrored x/y, unchanged z, metres
    deltas = H.mirrored_bbox_deltas(gate.stored_bbox_m,
                                    (*qa.bbox_min_m, *qa.bbox_max_m))
    assert deltas["max"] <= H.MIRROR_TOL_M
    lo, hi = qa.bbox_min_m, qa.bbox_max_m
    extent = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    assert H.FULL_BBOX_MIN_M <= extent <= H.FULL_BBOX_MAX_M
    assert report.mesh_summary["tags"].get(H.SOURCE_TAG, 0) > 0

    # deliverables written and self-describing
    assert report.mesh_path.is_file()
    qa_payload = json.loads(report.qa_json_path.read_text(encoding="utf-8"))
    assert qa_payload["schema"] == H.QA_SCHEMA
    assert qa_payload["qa"]["closed"] is True
    prov = json.loads(report.provenance_json_path.read_text(encoding="utf-8"))
    assert prov["schema"] == H.PROVENANCE_SCHEMA
    assert prov["provenance_gate"]["ok"] is True
    assert prov["lib_pins"]["run_lib_shas"]["hornlab_mesher"]
    assert prov["mesh_spec_full"]["quadrants"] == "1234"
