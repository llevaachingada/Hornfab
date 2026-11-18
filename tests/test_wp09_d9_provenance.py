"""WP 0.9 / D9 provenance package (R12/R12b, 2026-11-18 local implementation): the record digest
GATES geometry-from-record rebuilds while kernel implementation digests stay informational; new
recipes carry a ``record_digest`` block; mesh_meta echoes the mesher surfaceFit mode and flags the
interpolating->approximating fallback; each design row records the BUILD box (acoustic box + wall)
beside the acoustic box; a CPU tool classifies legacy recipes over runs/. All offline. No stored
row is rewritten."""
import numpy as np
import pytest

from hornlab_search.mesh.build import _surface_fit_meta
from hornlab_search.search.evaluate import _build_box_m
from tools.analysis.classify_recipes import (BRIDGE, REBUILDABLE, RECORD_REFUSED, UNVERIFIED,
                                             classify_design, _points_digest)


# ---------------------------------------------------------------- recipe_meta.record_digest

def test_recipe_meta_record_digest_block(monkeypatch):
    from types import SimpleNamespace
    from hornlab_search.design import recipe_meta
    from hornlab_search.design.generators import record_body

    class FakeRecord:
        sampler_version = "record-v2.0"

        def digest(self) -> str:
            return "abc123"

    d = SimpleNamespace(family="R-OSSE", params={})
    m = recipe_meta.recipe_metadata(d, record=FakeRecord())
    assert m["record_digest"] == {"value": "abc123", "source": "surface_record"}
    # canonical_record_v2 route: the grid meta already carries the gated digest.
    d2 = SimpleNamespace(family="FREEFORM",
                         params={"grid": {"rows": {"record_digest": "ff00",
                                                   "type": "canonical_record_v2"}}})
    m2 = recipe_meta.recipe_metadata(d2)
    assert m2["record_digest"] == {"value": "ff00", "source": "canonical_record_v2"}
    # plain formula recipe: explicit unknown.
    m3 = recipe_meta.recipe_metadata(d)
    assert m3["record_digest"] == {"value": None, "source": "not_recorded"}
    # Additive + non-identity: the block must not perturb the real points digest helper.
    inner = np.zeros((65, 61, 3))
    assert record_body.points_digest(inner) == record_body.points_digest(inner.copy())
    assert len(record_body.points_digest(inner)) == 64


# ---------------------------------------------------------------- surfaceFit echo

def test_surface_fit_meta_request_resolved_and_fallback():
    assert _surface_fit_meta({}, None) is None
    auto_interp = _surface_fit_meta({}, "interpolate")
    assert auto_interp == {"requested": "auto", "resolved": "interpolate", "fallback": False}
    fallback = _surface_fit_meta({}, "approximate")
    assert fallback == {"requested": "auto", "resolved": "approximate", "fallback": True}
    explicit = _surface_fit_meta({"mesh": {"surface_fit": "interpolate"}}, "approximate")
    assert explicit["fallback"] is False and explicit["requested"] == "interpolate"
    approx = _surface_fit_meta({"mesh": {"surface_fit": "approximate"}}, "approximate")
    assert approx["fallback"] is False


# ---------------------------------------------------------------- build box

def test_build_box_grows_by_the_resolved_wall_and_reports_unknown():
    from hornlab_search.types import MeshResult

    class D:
        family = "R-OSSE"
        params = {"wall_thickness_mm": 4.0}

    m = MeshResult(path="", n_triangles=10, n_dof=10, quadrants="1", symmetry_plane="z",
                   res_mm={}, bbox_m=(0.0, 0.0, 0.0, 0.5, 0.4, 0.2), seconds=0.0)
    assert _build_box_m(D(), m) == pytest.approx([-0.004, -0.004, -0.004, 0.504, 0.404, 0.204])
    assert _build_box_m(D(), None) is None

    class NoWall:
        family = "R-OSSE"
        params = {}

    # The mesher's 6.0 mm freestanding wall default is what recipe_meta resolves for R-OSSE
    # without wall_thickness_mm (family not ICW/FREEFORM, no enclosure) -> build box grows 0.006.
    assert _build_box_m(NoWall(), m) == pytest.approx(
        [-0.006, -0.006, -0.006, 0.506, 0.406, 0.206])


# ---------------------------------------------------------------- legacy classification

def _rows_block(type_, **extra):
    return {"grid": {"rows": {"type": type_, **extra}}}


def test_classify_kernel_digest_recipe():
    from hornlab_search.design.generators import klangfilm_lame_hv_core_family as core
    live = core.implementation_digest()
    ok = {"family": "FREEFORM",
          "generator": {"name": "grid"},
          "params": _rows_block("klangfilm_lame_hv_core", implementation_sha256=live)}
    assert classify_design(ok) == (REBUILDABLE, "klangfilm_lame_hv_core: kernel information-digest matches live")
    stale = json_replace(ok, live, "0" * 64)
    assert classify_design(stale)[0] == BRIDGE


def json_replace(payload, old, new):
    import json
    text = json.dumps(payload).replace(old, new)
    return json.loads(text)


def test_classify_record_body_and_param_routes():
    inner = (np.arange(65 * 61 * 3, dtype=float).reshape(65, 61, 3) * 0.001)
    digest = _points_digest(inner)
    good = {"family": "FREEFORM", "generator": {"name": "grid"},
            "params": _rows_block("canonical_record_v2", implementation_sha256=digest,
                                  points=inner.tolist(), sampler_version="record-v2.0")}
    assert classify_design(good)[0] == REBUILDABLE
    bad = json_replace(good, digest, "b" * 64)
    assert classify_design(bad)[0] == RECORD_REFUSED
    formula = {"family": "R-OSSE", "generator": {"name": "grid"},
               "params": _rows_block("osse_rounded")}
    assert classify_design(formula)[0] == REBUILDABLE
    assert classify_design({"family": "R-OSSE"})[0] == UNVERIFIED
