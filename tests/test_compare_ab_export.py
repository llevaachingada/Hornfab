"""A/B check: the BL handoff folder (offline; a tiny synthetic mesh stands in for the mesher)."""
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.compare import fake
from hornlab_search.compare.export_for_bl import balloon_angle_for_points, bl_balloon_count, blab_project, export_for_bl
from hornlab_search.compare.mshio import Mesh, read_msh, write_msh
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"


@pytest.fixture(scope="module")
def handoff(tmp_path_factory):
    d = tmp_path_factory.mktemp("ho")
    cfg = load_config(EX)
    design = DesignSpace.from_config(cfg).seed
    msh = fake.write_fake_quarter_msh(d / "q.msh")
    man = export_for_bl(None, d / "bl_handoff", cfg=cfg, design=design, mesh_path=msh, quadrants="1", label="t", hi_hz=20000.0)
    return d / "bl_handoff", man, fake.fake_quarter_mesh()


def test_handoff_files_exist(handoff):
    d, man, _ = handoff
    for rel in ("FOR_YOUR_FRIEND.md", "handoff.json", "horn.blab.json", "request.json", "request_float64.json",
                "frequencies_hz.txt", "mesh/horn_full_m.msh", "mesh/hornfab_native_q1.msh",
                "results_from_friend/README.txt", "results_from_friend/polar", "results_from_friend/headless_run"):
        assert (d / rel).exists(), rel
    assert json.loads((d / "handoff.json").read_text())["design"]["design_hash"] == man["design"]["design_hash"]


def test_full_mesh_is_metres_full_domain_with_tags_and_areas(handoff):
    d, man, q = handoff
    full = read_msh(d / "mesh" / "horn_full_m.msh")
    assert full.tri.shape[0] == 4 * q.tri.shape[0] and set(full.names.values()) == {"SD1G0", "SD1D1001"}
    assert 0.02 <= max(np.ptp(full.xyz, axis=0)) <= 5.0
    assert man["mesh"]["driven_area_m2_full"] == pytest.approx(4 * q.tag_areas()[2])
    assert man["mesh"]["driven_tag"] == 2 and man["mesh"]["units"] == "metres" and man["mesh"]["scale_to_m"] == 1.0
    assert man["mesh"]["symmetry_in_blab"] == "off" and man["mesh"]["native"]["quadrant_factor"] == 4
    assert len(man["mesh"]["sha256"]) == 64


def test_blab_project_matches_boundary_lab_fixture_keys(handoff):
    d, man, _ = handoff
    p = json.loads((d / "horn.blab.json").read_text())
    ps = p["physical_system"]
    assert p["schema_version"] == 10 and p["symmetry"] == "off" and ps["model_version"] == 1
    assert ps["meshes"][0]["scale_to_m"] == 1.0 and ps["meshes"][0]["purpose"] == "bem_surface"
    assert p["imported_meshes"][0]["scale_factor"] == 1.0
    assert ps["regions"][0]["kind"] == "unbounded_air"
    kinds = {b["kind"]: b["group"] for b in ps["boundaries"]}
    assert kinds["rigid"]["tag"] == 1 and kinds["moving"]["tag"] == 2 and kinds["moving"]["name"] == "SD1D1001"
    assert ps["components"][0]["kind"] == "ideal_velocity_source" and ps["excitation_ports"][0]["kind"] == "normal_velocity"
    pref = p["project_preferences"]
    assert pref["normalized_channel_correction"] is False and pref["spherical_sampling_enabled"] is True
    assert pref["freq_min_hz"] == 100 and pref["freq_max_hz"] == 20000 and pref["freq_count"] == 93
    assert pref["polar_angle_step_deg"] == 2.5 and pref["polar_observation_distance_m"] == 2.0
    assert pref["spl_min_db"] <= -60 and pref["horizontal_normalization_angle"] == 0.0


def test_frequency_list_request_and_balloon_rule(handoff):
    d, man, _ = handoff
    f = [float(x) for x in (d / "frequencies_hz.txt").read_text().split()]
    assert f == man["frequencies"]["freqs_hz"] and len(f) == 93
    assert json.loads((d / "request.json").read_text())["frequencies_hz"] == f
    assert json.loads((d / "request_float64.json").read_text())["solver_options"] == {"precision": "float64"}
    assert bl_balloon_count(balloon_angle_for_points(2048)) in range(2040, 2056)        # BL: round(41253 / a^2)


def test_friend_instructions_name_the_traps_and_the_drop_folders(handoff):
    t = (handoff[0] / "FOR_YOUR_FRIEND.md").read_text()
    for needle in ("Normalized Channel Correction", "OFF", "Export Polar Data", "Export On-Axis Data", "Export Balloon Data",
                   "results_from_friend/polar", "results_from_friend/on_axis/on_axis.txt", "blab project solve", "symmetry", "metres"):
        assert needle in t, needle


def test_symmetric_alternative_project_uses_the_native_mesh_and_blab_xy(handoff):
    d, man, _ = handoff
    alt = json.loads((d / "horn_symmetric.blab.json").read_text())
    assert alt["symmetry"] == "xy" and alt["physical_system"]["meshes"][0]["file"] == "mesh/hornfab_native_q1.msh"
    assert alt["physical_system"]["meshes"][0]["scale_to_m"] == 1.0
    assert man["mesh"]["symmetric_alternative"]["blab_symmetry"] == "xy"
    assert "horn_symmetric.blab.json" in (d / "FOR_YOUR_FRIEND.md").read_text()


def test_default_top_frequency_follows_what_the_mesh_resolves(tmp_path):
    cfg = load_config(EX)
    man = export_for_bl(None, tmp_path / "h", cfg=cfg, design=DesignSpace.from_config(cfg).seed,
                        mesh_path=fake.write_fake_quarter_msh(tmp_path / "q.msh"), quadrants="1", label="a")
    q = man["mesh"]["quality"]["f_valid_p95_hz"]
    assert man["frequencies"]["hi_hz"] == np.floor(q / 100.0) * 100.0 and man["frequencies"]["hi_hz"] < 20000


def test_keep_symmetry_exports_reduced_mesh_with_blab_flag(tmp_path):
    cfg = load_config(EX)
    man = export_for_bl(None, tmp_path / "h", cfg=cfg, design=DesignSpace.from_config(cfg).seed,
                        mesh_path=fake.write_fake_quarter_msh(tmp_path / "q.msh"), quadrants="1", keep_symmetry=True, label="s")
    assert man["mesh"]["symmetry_in_blab"] == "xy"
    assert json.loads((tmp_path / "h" / "horn.blab.json").read_text())["symmetry"] == "xy"
    assert read_msh(tmp_path / "h" / "mesh" / "horn_full_m.msh").tri.shape[0] == man["mesh"]["native"]["n_triangles"]


def test_export_refuses_wrong_units_unknown_groups_and_missing_source_tag(tmp_path):
    cfg = load_config(EX)
    design = DesignSpace.from_config(cfg).seed
    q = fake.fake_quarter_mesh()
    big = Mesh(q.xyz * 1000.0, q.tri, q.phys, q.names)                   # a millimetre mesh
    write_msh(big, tmp_path / "mm.msh")
    with pytest.raises(ValueError, match="units"):
        export_for_bl(None, tmp_path / "a", cfg=cfg, design=design, mesh_path=tmp_path / "mm.msh", quadrants="1")
    odd = Mesh(q.xyz, q.tri, np.where(q.phys == 1, 3, 2), q.names)
    write_msh(odd, tmp_path / "odd.msh")
    with pytest.raises(ValueError, match="unknown physical group"):
        export_for_bl(None, tmp_path / "b", cfg=cfg, design=design, mesh_path=tmp_path / "odd.msh", quadrants="1")
    nosrc = Mesh(q.xyz, q.tri, np.ones_like(q.phys), q.names)
    write_msh(nosrc, tmp_path / "ns.msh")
    with pytest.raises(ValueError, match="tag 2"):
        export_for_bl(None, tmp_path / "c", cfg=cfg, design=design, mesh_path=tmp_path / "ns.msh", quadrants="1")
    with pytest.raises(ValueError, match="no existing mesh"):
        export_for_bl(None, tmp_path / "d", cfg=cfg, design=design, quadrants="1")


def test_blab_project_requires_whole_hz_end_points():
    with pytest.raises(ValueError, match="integer"):
        blab_project(mesh_file="m.msh", name="x", freqs_hz=[100.5, 200.0], distance_m=2.0, angle_step_deg=2.5, balloon_angle_deg=5.0)
