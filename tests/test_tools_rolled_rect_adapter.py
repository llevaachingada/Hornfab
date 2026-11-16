from copy import deepcopy

import numpy as np
import pytest

from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid
from tools.geometry import rolled_rect, rolled_rect_cli as adapter


@pytest.fixture
def sample():
    shape = {"width_mm": 542., "height_mm": 299., "depth_mm": 238., "depth_h_ratio": .68, "decay": .7,
             "rect_exponent": 12., "rect_turn_deg": 65., "throat_turn_deg": 25.,
             "terminal_deg": 270., "pucker_h_mm": 0., "pucker_v_mm": 0.,
             "pucker_start_deg": 55., "wall_thickness_mm": 3., "n_phi": 25, "n_s": 40}
    spec = {"name": "grid", "rows": {"type": "rolled_rect"},
            **{k: shape[k] for k in ("wall_thickness_mm", "n_phi", "n_s")}}
    knobs = {"g_" + k: v for k, v in shape.items() if k in adapter.SHAPE_KNOBS}
    brief = {"driver": {"exit_radius_mm": 18., "exit_angle_deg": 2.},
             "envelope": {"max_mouth_w_mm": 600., "max_mouth_h_mm": 480., "max_depth_mm": 480.}}
    return shape, spec, knobs, brief


@pytest.fixture
def patched(monkeypatch):
    for name in ("design_params", "validate_grid_params", "rows_grid_points", "envelope_extents"):
        monkeypatch.setattr(grid, name, getattr(grid, name))
    monkeypatch.setattr(adapter, "_INSTALLED", False)
    adapter.install()


def test_stock_rejects_custom_type(sample):
    _, spec, knobs, brief = sample
    with pytest.raises(grid.registry.GeneratorError, match="unknown rows type"):
        grid.design_params(spec, knobs, brief)


def test_roundtrip_and_geometry(sample, patched):
    shape, spec, knobs, brief = sample
    space = GeneratedSpace(spec, brief, knobs, {})
    design = space.seed
    families.validate(design)
    recipe = design.params["grid"]
    assert recipe["rows"]["implementation_sha256"] == adapter.implementation_digest()
    assert recipe["rows"]["driver"] == brief["driver"]
    assert recipe["knobs"] == knobs
    spec2 = {k: v for k, v in recipe.items() if k != "knobs"}
    actual, meta = grid.rows_grid_points(spec2, knobs, brief)
    expected, _ = rolled_rect.make_grid(shape, brief)
    np.testing.assert_array_equal(actual, expected)
    assert meta["mouth_w_mm"] <= 600
    assert grid.envelope_extents(spec2, knobs, brief) == (meta["mouth_w_mm"], meta["mouth_h_mm"], meta["x_span_mm"])
    assert space.design_from_knobs(knobs).hash() == design.hash()


def test_stale_driver_or_digest_fails(sample, patched):
    _, spec, knobs, brief = sample
    block = grid.design_params(spec, knobs, brief)["grid"]
    changed = deepcopy(block)
    changed["rows"]["implementation_sha256"] = "0" * 64
    with pytest.raises(grid.registry.GeneratorError, match="digest"):
        grid.validate_grid_params(changed)
    newer = deepcopy(brief)
    newer["driver"]["exit_radius_mm"] = 19.
    with pytest.raises(grid.registry.GeneratorError, match="driver differs"):
        grid.rows_grid_points(block, knobs, newer)


def test_invalid_shape_and_envelope_refuse(sample, patched):
    _, spec, knobs, brief = sample
    bad = dict(knobs, g_width_mm=100.)
    with pytest.raises(grid.registry.GeneratorError, match="landscape"):
        grid.design_params(spec, bad, brief)
    bad = dict(knobs, g_width_mm=700.)
    with pytest.raises(grid.registry.GeneratorError, match="invalid_envelope"):
        grid.design_params(spec, bad, brief)
    with pytest.raises(grid.registry.GeneratorError, match="unknown"):
        grid.design_params(spec, dict(knobs, g_unrecognized=1.), brief)
    with pytest.raises(grid.registry.GeneratorError, match="base requires zero pucker"):
        grid.design_params(spec, dict(knobs, g_pucker_h_mm=1.), brief)


def test_noncustom_delegates(sample, monkeypatch):
    calls = []
    sentinel = object()
    def original(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel
    monkeypatch.setattr(grid, "design_params", original)
    monkeypatch.setattr(grid, "validate_grid_params", original)
    monkeypatch.setattr(grid, "rows_grid_points", original)
    monkeypatch.setattr(grid, "envelope_extents", original)
    monkeypatch.setattr(adapter, "_INSTALLED", False)
    adapter.install()
    _, spec, knobs, brief = sample
    spec["rows"]["type"] = "osse_rollback"
    assert grid.design_params(spec, knobs, brief) is sentinel
    assert grid.validate_grid_params(spec) is sentinel
    assert grid.rows_grid_points(spec, knobs, brief) is sentinel
    assert grid.envelope_extents(spec, knobs, brief) is sentinel
    assert len(calls) == 4


def test_digest_is_stable_across_git_line_endings(tmp_path, monkeypatch):
    geometry_path = tmp_path / "geometry.py"
    adapter_path = tmp_path / "adapter.py"
    monkeypatch.setattr(adapter.geometry, "__file__", str(geometry_path))
    monkeypatch.setattr(adapter, "__file__", str(adapter_path))
    for path in (geometry_path, adapter_path):
        path.write_bytes(b"first\nsecond\n")
    expected = adapter.implementation_digest()
    for path in (geometry_path, adapter_path):
        path.write_bytes(b"first\r\nsecond\r\n")
    assert adapter.implementation_digest() == expected
