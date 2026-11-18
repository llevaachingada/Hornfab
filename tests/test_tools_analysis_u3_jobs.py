"""WP 4.2/4.3 (2026-11-17): record-body family + U3 job configs that load and mesh."""
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.design.generators import record_body as RB
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.geometry import record as R
from tests.conftest import requires_mesher
from tests.test_tools_analysis_senior_plan_evidence import _run
from tools.analysis import u3_jobs


def test_record_body_digest_matches_record_and_gates_geometry():
    from tests.test_geometry_record import _elliptic_cone
    rec = R.sample_record(_elliptic_cone())
    spec = RB.spec_from_record(rec, wall_thickness_mm=3.0, source_auto_angle_deg=10.0)
    assert spec["rows"]["implementation_sha256"] == rec.digest()
    g = RB.resolve_grid(spec, {"driver": {}})
    assert np.allclose(g["inner_points"], rec.inner) and g["outer_points"].shape == rec.inner.shape
    spec["rows"]["points"][3][5][0] += 0.01                       # a silent geometry change
    with pytest.raises(GeneratorError, match="digest"):
        RB.resolve_grid(spec, {})
    with pytest.raises(GeneratorError, match="digest"):
        RB.validate_grid_params(spec)


def test_u3_jobs_write_loadable_configs(tmp_path):
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    run, _ = _run(tmp_path)
    m = u3_jobs.write_jobs(run, "h1", tmp_path / "jobs")
    assert set(m["arms"]) == {"control", "vt_460", "vt_480", "term_sides", "term_topbottom",
                              "steer_early", "steer_late", "diag_pull"}
    c = load_config(tmp_path / "jobs" / "control.yaml")
    seed = DesignSpace.from_config(c).seed
    assert seed.params["grid"]["rows"]["implementation_sha256"] == m["record_digest"]
    assert m["arms"]["control"]["valid"] is True


@requires_mesher
def test_u3_control_config_meshes_like_the_host(tmp_path):
    pytest.importorskip("gmsh")
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.build import build_mesh
    run, _ = _run(tmp_path)
    u3_jobs.write_jobs(run, "h1", tmp_path / "jobs")
    c = load_config(tmp_path / "jobs" / "control.yaml")
    m = build_mesh(DesignSpace.from_config(c).seed, mesh_spec("screen", c), c, tmp_path / "m",
                   mode="screen")
    b = m.bbox_m
    assert b[3] * 2000 == pytest.approx(560.0, abs=1.0) and b[4] * 2000 == pytest.approx(350.0, abs=1.0)
