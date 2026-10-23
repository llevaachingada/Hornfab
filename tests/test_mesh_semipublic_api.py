"""Guard: the semi-public mesher APIs we call keep the signatures we rely on (beta pass A3).

Same intent as ``test_mesh_pin.py``: a mesher change that would silently alter how we call these must
fail loudly. Signatures recorded at mesher pin b922e807 (0.2.4) and unchanged at upstream 4573bc90.
CI installs inert stubs, so a missing attribute skips instead of failing.
"""
from __future__ import annotations

import importlib
import inspect

import pytest

from conftest import requires_mesher


def _get(mod: str, name: str):
    try:
        obj = getattr(importlib.import_module(mod), name)
    except (ImportError, AttributeError):
        pytest.skip(f"{mod}.{name} not available (stub install)")
    return obj


def _params(fn):
    return [(p.name, p.kind, p.default) for p in inspect.signature(fn).parameters.values()]


@requires_mesher
def test_profile_points_signature():
    # used by design/generators/registry.py: profile_points(prm, 600, phi)
    fn = _get("hornlab_mesher.profile_formulas", "profile_points")
    names = [n for n, *_ in _params(fn)]
    assert names[:3] == ["params", "n_axial", "phi"]
    assert inspect.signature(fn).parameters["phi"].default == 0.0


@requires_mesher
def test_build_freeform_geometry_signature():
    fn = _get("hornlab_mesher.freeform", "build_freeform_geometry")
    assert [n for n, *_ in _params(fn)] == ["params"]


@requires_mesher
def test_freeform_curvature_guard_margin_is_0_4():
    # the FREEFORM outer-shell guard: thickness x concave curvature < 0.4 (generated horns use 3 mm)
    _get("hornlab_mesher.freeform", "_validate_freeform_config")
    cls = _get("hornlab_mesher.freeform", "FreeformGeometry")
    sig = inspect.signature(cls.surface_curvature_report)
    assert "wall_thickness_mm" in sig.parameters
    assert sig.parameters["margin"].default == 0.4


@requires_mesher
def test_config_builder_build_point_grid_signature():
    # mesh/grid.py delegates to config_builder.build_point_grid(params, *, defer_osse_offset_repair)
    fn = _get("hornlab_mesher.config_builder", "build_point_grid")
    sig = inspect.signature(fn)
    assert list(sig.parameters)[0] == "params"
    assert sig.parameters["defer_osse_offset_repair"].kind is inspect.Parameter.KEYWORD_ONLY
