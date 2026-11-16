"""CPU contracts for the native rolled family and its frozen parent surfaces."""
import copy
import json
import math
import subprocess
import sys
import tomllib
from importlib import resources

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config
from hornlab_search.design.space import Bound, DesignSpace
from hornlab_search.design.generators import rolled_family as rf
from hornlab_search.design.generators.registry import GeneratorError


@pytest.fixture(params=['rect', 'section'])
def family(request):
    cfg = load_config(REPO / 'examples/typologies/rolled_family_2026-11-15' /
                      f'rf__{request.param}_radial_v7.yaml')
    return DesignSpace.from_config(cfg)


def resolve(space, knobs=None):
    if knobs is None:
        block = space.seed.params['grid']
    else:
        block = rf.design_params(space.gen, knobs, space.brief)['grid']
    return rf.resolve_grid(block, space.brief)


def neutral(space):
    knobs = dict(space.seed_knobs)
    knobs['g_inward_h_mm'] = knobs['g_inward_v_mm'] = 0.0
    return knobs


def test_zero_matches_frozen_parent_inner_and_outer(family):
    _, _, parent = rf._shape(family.gen, neutral(family), brief=family.brief)
    # Load the frozen research modules in an isolated interpreter. The explicit
    # namespace is confined to that child; it cannot mask the canonical import.
    script = '''import json, sys, types
from pathlib import Path
repo = Path(sys.argv[1])
pkg = types.ModuleType("tools"); pkg.__path__ = [str(repo / "tools")]; sys.modules["tools"] = pkg
from tools.geometry import rolled_rect, crowe_panel
from hornlab_search.design.generators import grid
data = json.load(sys.stdin)
kernel = rolled_rect if data["kind"] == "rect" else crowe_panel
inner, _ = kernel.make_grid(data["shape"], {"driver": data["driver"]})
outer = (grid.grid_outer_points(inner, data["shape"]["wall_thickness_mm"])
         if data["kind"] == "rect" else kernel.outer_points(inner, data["shape"]))
print(json.dumps([inner.tolist(), outer.tolist()]))
'''
    kind = 'rect' if family.gen['rows']['type'] == rf.KINDS[0] else 'section'
    proc = subprocess.run([sys.executable, '-c', script, str(REPO)], cwd=REPO,
                          input=json.dumps({'kind': kind, 'shape': parent,
                                            'driver': family.brief['driver']}),
                          text=True, capture_output=True, check=True, timeout=60)
    expected, expected_outer = map(np.asarray, json.loads(proc.stdout))
    actual = resolve(family, neutral(family))
    np.testing.assert_array_equal(actual['inner_points'], expected)
    np.testing.assert_array_equal(actual['outer_points'], expected_outer)


def test_radial_displacement_and_source_and_return(family):
    parent = resolve(family, neutral(family))
    treated = resolve(family)
    base, inner = parent['inner_points'], treated['inner_points']
    rho0, rho = np.hypot(base[..., 0], base[..., 1]), np.hypot(inner[..., 0], inner[..., 1])
    assert np.all(rho <= rho0 + 1e-10)
    np.testing.assert_array_equal(inner[..., 2], base[..., 2])
    station = np.array(treated['meta']['stations'])
    peak = np.argmax(rf.relief_window(treated['meta']['shape'], station))
    w = rf.relief_window(treated['meta']['shape'], station)[peak]
    assert w > .99
    np.testing.assert_allclose(rho0[[0, -1], peak] - rho[[0, -1], peak],
                               [family.seed_knobs['g_inward_h_mm']*w,
                                family.seed_knobs['g_inward_v_mm']*w], atol=1e-9)
    psi = np.arctan2(base[:, peak, 1]/base[-1, peak, 1],
                     base[:, peak, 0]/base[0, peak, 0])
    h, v = family.seed_knobs['g_inward_h_mm'], family.seed_knobs['g_inward_v_mm']
    expected = (h*np.cos(psi)**2 + v*np.sin(psi)**2)*np.cos(2*psi)**2*w
    np.testing.assert_allclose(rho0[:, peak]-rho[:, peak], expected, atol=1e-9)
    assert np.interp(np.pi/4, psi, expected) < .01
    np.testing.assert_array_equal(inner[:, station <= family.seed_knobs['g_relief_start_s']],
                                  base[:, station <= family.seed_knobs['g_relief_start_s']])
    np.testing.assert_array_equal(inner[:, -2:], base[:, -2:])
    np.testing.assert_allclose(treated['outer_points'][:, -1], parent['outer_points'][:, -1], atol=1e-10)
    if family.gen['rows']['type'] == rf.KINDS[1]:
        np.testing.assert_allclose(treated['outer_points'], parent['outer_points'], atol=1e-10)


def test_driver_tangent_normals_and_forward_no_constriction(family):
    shape, kernel, parent = rf._shape(family.gen, family.seed_knobs, brief=family.brief)
    driver = family.brief['driver']
    points = kernel.surface_at(parent, driver, [0, 1e-7], np.linspace(0, np.pi/2, 9))
    radii = np.hypot(points[..., 0], points[..., 1])
    np.testing.assert_allclose(radii[:, 0], driver['exit_radius_mm'], atol=1e-8)
    slope = (radii[:, 1]-radii[:, 0])/(points[:, 1, 2]-points[:, 0, 2])
    np.testing.assert_allclose(slope, math.tan(math.radians(2)), atol=1e-6)
    treated, reference = resolve(family), resolve(family, neutral(family))
    for sheet in (treated['inner_points'], treated['outer_points']):
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        assert np.isfinite(normal).all() and np.min(np.linalg.norm(normal, axis=-1)) > 1e-9
    for row, orig in zip(treated['inner_points'], reference['inner_points']):
        forward = np.argmax(orig[:, 2])
        assert np.min(np.diff(np.hypot(row[:forward+1, 0], row[:forward+1, 1]))) >= -1e-6


@pytest.mark.parametrize('edit', ['negative', 'inactive', 'window', 'missing'])
def test_invalid_shape_is_rejected(family, edit):
    knobs = dict(family.seed_knobs)
    if edit == 'negative': knobs['g_inward_h_mm'] = -1
    if edit == 'inactive': knobs['g_axial_h_mm'] = 1
    if edit == 'window': knobs['g_relief_peak_s'] = knobs['g_relief_start_s']
    if edit == 'missing': del knobs['g_width_mm']
    with pytest.raises(GeneratorError):
        rf.design_params(family.gen, knobs, family.brief)


@pytest.mark.parametrize('edit', ['missing', 'out_of_bound', 'fixed_mismatch', 'inactive_bounds', 'dormant_position', 'overlap'])
def test_invalid_search_contract_is_rejected(family, edit):
    seed, bounds = dict(family.seed_knobs), dict(family.bounds)
    if edit == 'missing': del seed['g_width_mm']
    if edit == 'out_of_bound': seed['g_inward_h_mm'] = bounds['g_inward_h_mm'].hi + 1
    if edit == 'fixed_mismatch': bounds['g_width_mm'] = Bound(seed['g_width_mm']-1, seed['g_width_mm']-1, search=False)
    if edit == 'inactive_bounds': bounds['g_axial_h_mm'] = Bound(0, 1)
    if edit == 'dormant_position': bounds['g_relief_peak_s'] = Bound(.79, .81)
    if edit == 'overlap': bounds['g_relief_peak_s'] = Bound(.49, .81)
    with pytest.raises(GeneratorError):
        rf.validate_search_config(family.gen, seed, bounds, family.brief)


def test_saved_recipe_replays_and_digest_driver_are_guarded(family):
    block = json.loads(json.dumps(family.seed.params['grid']))
    original = resolve(family)
    replay = rf.resolve_grid(block, family.brief)
    for key in ('inner_points', 'outer_points'):
        np.testing.assert_array_equal(original[key], replay[key])
    for key in ('schema', 'implementation_sha256'):
        bad = copy.deepcopy(block)
        bad['rows'][key] = 'invalid'
        with pytest.raises(GeneratorError): rf.resolve_grid(bad, family.brief)
    bad = copy.deepcopy(block)
    bad['rows']['driver']['exit_radius_mm'] += 1
    with pytest.raises(GeneratorError): rf.resolve_grid(bad, family.brief)


def test_five_searched_knobs_have_independent_surface_effects(family):
    keys = family.keys()
    assert len(keys) == 5
    assert all(.001 < x < .999 for x in family.normalize(family.seed))
    x = family.normalize(family.seed)
    columns = []
    for i in range(len(keys)):
        lo, hi = x.copy(), x.copy()
        lo[i] -= .001
        hi[i] += .001
        a, b = family.denormalize(lo), family.denormalize(hi)
        assert 'grid' in a.params and 'grid' in b.params
        pa = rf.resolve_grid(a.params['grid'], family.brief)['inner_points']
        pb = rf.resolve_grid(b.params['grid'], family.brief)['inner_points']
        columns.append(((pb-pa)/.002).ravel())
    jac = np.column_stack(columns)
    norms = np.linalg.norm(jac, axis=0)
    assert np.all(norms > 1e-5), dict(zip(keys, norms))
    singular = np.linalg.svd(jac/norms, compute_uv=False)
    assert singular[-1] > 1e-4, (keys, singular)


def test_packaged_reference_and_fresh_process_do_not_depend_on_tools():
    package = 'hornlab_search.design.generators'
    manifest = tomllib.loads((REPO / 'pyproject.toml').read_text(encoding='utf-8'))
    assert 'data/*.yaml' in manifest['tool']['setuptools']['package-data'][package]
    assert resources.files(package).joinpath('data/crowe_section_reference_v1.yaml').is_file()
    script = '''import sys
from pathlib import Path
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators import rolled_family
for name in ("rect", "section"):
    path = Path(sys.argv[1]) / "examples/typologies/rolled_family_2026-11-15" / ("rf__" + name + "_radial_v7.yaml")
    space = DesignSpace.from_config(load_config(path))
    rolled_family.resolve_grid(space.seed.params["grid"], space.brief)
assert not any(name == "tools" or name.startswith("tools.") for name in sys.modules)
'''
    subprocess.run([sys.executable, '-c', script, str(REPO)], cwd=REPO,
                   capture_output=True, text=True, check=True, timeout=60)


def test_return_inverse_roundoff_uses_its_own_branch_domain():
    # A real uniform-box sample found in the first full audit: subtracting and
    # readding the pivot put the last return radius a few ulps below its domain.
    cfg = load_config(REPO/'examples/typologies/rolled_family_2026-11-15/rf__section_control_v7.yaml')
    space = DesignSpace.from_config(cfg)
    design = space.denormalize([.9274239286245599, .9679261899246464, .014706304965369288])
    assert '_generator_error' not in design.params
    geometry = rf.resolve_grid(design.params['grid'], cfg.brief)
    assert all(np.isfinite(geometry[k]).all() for k in ('inner_points', 'outer_points'))
