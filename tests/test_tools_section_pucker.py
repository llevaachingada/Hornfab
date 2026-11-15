"""CPU-only contract tests for the opt-in section-pucker study."""
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.interpolate import PchipInterpolator

from hornlab_search.config import load_config
from tools.geometry import crowe_panel as parent, section_pucker as pucker

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / 'examples/typologies/section_pucker_2026-11-15'
OLD = ROOT / 'examples/typologies/rolled_rect_2026-11-15/rr__crowe_panel_es600_v7.yaml'


@pytest.fixture(scope='module')
def inputs():
    cfg = load_config(CONFIGS / 'sp__strong_v7.yaml')
    shape = {k: cfg.seed_params['g_'+k] for k in pucker.SHAPE_KEYS-{'n_phi','n_s','wall_thickness_mm'}}
    shape.update({k: cfg.generator[k] for k in ('n_phi','n_s','wall_thickness_mm')})
    return shape, cfg.brief


def parent_shape(shape):
    return {k: shape[k] for k in parent.SHAPE_KEYS}


def test_zero_is_exact_parent_grid_and_outer(inputs):
    shape, brief = inputs
    shape = {**shape, 'pucker_h_mm': 0., 'pucker_v_mm': 0.}
    actual, meta = pucker.make_grid(shape, brief)
    expected, base_meta = parent.make_grid(parent_shape(shape), brief)
    assert meta['stations'] == base_meta['stations']
    assert np.array_equal(actual, expected)
    assert np.array_equal(pucker.outer_points(actual, shape), parent.outer_points(expected, parent_shape(shape)))


def test_throat_symmetry_planes_and_axial_only(inputs):
    shape, brief = inputs
    s = np.r_[0., 1e-6, np.linspace(.1, 1., 101)]
    phi = np.linspace(0, math.pi/2, 41)
    points = pucker.surface_at(shape, brief['driver'], s, phi)
    base = parent.surface_at(parent_shape(shape), brief['driver'], s, phi)
    assert np.array_equal(points[..., :2], base[..., :2])
    assert np.array_equal(points[0, :, 1], np.zeros(len(s)))
    assert np.array_equal(points[-1, :, 0], np.zeros(len(s)))
    r = np.hypot(points[..., 0], points[..., 1])
    np.testing.assert_allclose(r[:, 0], 18., atol=1e-10)
    np.testing.assert_allclose((r[:, 1]-r[:, 0])/(points[:, 1, 2]-points[:, 0, 2]), math.tan(math.radians(2)), atol=1e-7)


def test_peak_h_v_and_normalized_diagonal(inputs):
    shape, brief = inputs
    shape = {**shape, 'pucker_h_mm': 4., 'pucker_v_mm': 6.}
    s = shape['pucker_peak_s']
    ds, vertical, joint, *_ = parent._sweep(parent_shape(shape), brief['driver'])
    # Recover the meridian dimensions independently from the same continuous sweep.
    h = PchipInterpolator(ds, joint[:, 0])(s)
    v = PchipInterpolator(ds, vertical[:, 0])(s)
    def normalized_delta(phi):
        p = parent.surface_at(parent_shape(shape), brief['driver'], [s], [phi])[0, 0]
        return p[1]/v-p[0]/h
    phi_diag = brentq(normalized_delta, 0., math.pi/2)
    phis = [0., phi_diag, math.pi/2]
    before = parent.surface_at(parent_shape(shape), brief['driver'], [s], phis)
    after = pucker.surface_at(shape, brief['driver'], [s], phis)
    np.testing.assert_allclose((after-before)[:, 0, 2], [4., -5., 6.], atol=2e-3, rtol=0)


def test_quintic_window_boundaries_and_derivatives(inputs):
    shape, _ = inputs
    start, peak, end = (shape[k] for k in ('pucker_start_s','pucker_peak_s','pucker_end_s'))
    np.testing.assert_array_equal(pucker.window(shape, [start-.01, start, peak, end, end+.01]), [0., 0., 1., 0., 0.])
    eps = 1e-6
    for x in (start, peak, end):
        vals = pucker.window(shape, [x-eps, x, x+eps])
        assert abs((vals[2]-vals[0])/(2*eps)) < 1e-5
        assert abs((vals[2]-2*vals[1]+vals[0])/eps**2) < .02
    t = .37
    mid = start+t*(peak-start)
    assert pucker.window(shape, [mid])[0] == pytest.approx(6*t**5-15*t**4+10*t**3, abs=1e-14)


@pytest.mark.parametrize('h,v', [(4.,6.), (4.,12.), (10.,6.), (10.,12.)])
def test_bounds_finite_normals_return_and_outer_attachment(inputs, h, v):
    shape, brief = inputs
    shape = {**shape, 'pucker_h_mm': h, 'pucker_v_mm': v}
    actual, meta = pucker.make_grid(shape, brief)
    base, _ = parent.make_grid(parent_shape(shape), brief)
    assert np.isfinite(actual).all()
    assert np.array_equal(actual[..., :2], base[..., :2])
    assert np.array_equal(actual[:, -2:], base[:, -2:])
    assert np.array_equal(pucker.outer_points(actual, shape), parent.outer_points(base, parent_shape(shape)))
    normal = np.cross(np.gradient(actual, axis=0), np.gradient(actual, axis=1))
    assert np.isfinite(normal).all() and np.min(np.linalg.norm(normal, axis=-1)) > 1e-8
    # H rolls inward; the frozen V section instead has a flat-radius rear tail.
    radius = np.hypot(actual[0, :, 0], actual[0, :, 1])
    assert radius[-1] < radius.max()-1
    for row in actual[[0, -1]]:
        assert row[-1, 2] < row[:, 2].max()-1
    assert meta['stations'][-1] == 1.


@pytest.mark.parametrize('change', [
    {'pucker_start_s': .8}, {'pucker_peak_s': .96}, {'pucker_end_s': 1.},
    {'pucker_start_s': float('nan')}, {'pucker_peak_s': float('inf')},
    {'pucker_h_mm': -1.}, {'pucker_v_mm': float('nan')}, {'pucker_h_mm': 100.},
])
def test_invalid_shape_rejected(inputs, change):
    shape, brief = inputs
    with pytest.raises(ValueError):
        pucker.make_grid({**shape, **change}, brief)


def run_python(code, *args):
    result = subprocess.run([sys.executable, '-c', code, *map(str, args)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_recipe_digest_and_stock_rejection(tmp_path):
    recipe = tmp_path / 'recipe.json'
    run_python(r'''
import json, sys, tempfile
from pathlib import Path
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design import families
from tools.geometry import section_pucker_cli as cli
cfg=load_config(sys.argv[1])
try: DesignSpace.from_config(cfg)
except Exception: pass
else: raise AssertionError('stock accepted experimental config')
cli.install()
d=DesignSpace.from_config(cfg).seed
families.validate(d)
r=d.params['grid']['rows']
assert r['type']=='section_pucker' and r['implementation_sha256']==cli.implementation_digest()
Path(sys.argv[2]).write_text(json.dumps(d.params))
with tempfile.TemporaryDirectory() as td:
    for obj, attr in [(cli.crowe_panel, '__file__'), (cli.crowe_panel.base, '__file__'), (cli.crowe_panel, 'REFERENCE')]:
        original=getattr(obj, attr); path=Path(td)/str(len(list(Path(td).iterdir())))
        path.write_bytes(Path(original).read_bytes()+b'\n# changed\n')
        old=cli.implementation_digest(); setattr(obj, attr, path)
        assert cli.implementation_digest()!=old, attr
        setattr(obj, attr, original)
''', CONFIGS / 'sp__strong_v7.yaml', recipe)
    run_python(r'''
import json, sys
from hornlab_search.design import families
from hornlab_search.types import Design
from tools.geometry import section_pucker_cli as cli
params=json.load(open(sys.argv[1])); cli.install()
d=Design('FREEFORM', params)
families.validate(d)
from hornlab_search.design.generators import grid
from hornlab_search.config import load_config
brief=load_config(sys.argv[2]).brief
block=params['grid']
points, meta=grid.rows_grid_points(block, block['knobs'], brief)
assert points.shape == (block['n_phi'], block['n_s']+1, 3)
assert meta['implementation_sha256'] == block['rows']['implementation_sha256']
block['rows']['implementation_sha256']='0'*64
try: families.validate(d)
except Exception: pass
else: raise AssertionError('stale source digest accepted')
''', recipe, CONFIGS / 'sp__strong_v7.yaml')
    for wrapper in ('stock', 'old'):
        run_python(r'''
import json, sys
from hornlab_search.design import families
from hornlab_search.types import Design
if sys.argv[2]=='old':
    from tools.geometry import crowe_panel_cli
    crowe_panel_cli.install()
try: families.validate(Design('FREEFORM', json.load(open(sys.argv[1]))))
except Exception: pass
else: raise AssertionError('foreign saved recipe accepted')
''', recipe, wrapper)


def test_verify_night_routes_own_wrapper(monkeypatch):
    from tools.geometry import section_pucker_cli, verify_rolled_rect_night
    calls = []
    monkeypatch.setattr(verify_rolled_rect_night, 'WRAPPER', verify_rolled_rect_night.WRAPPER)
    monkeypatch.setattr(verify_rolled_rect_night, 'main', lambda args: calls.append((args, verify_rolled_rect_night.WRAPPER)) or 0)
    assert section_pucker_cli.main(['verify-night', '--night', 'demo', '--jobs', 'panel']) == 0
    assert calls == [(['--night', 'demo', '--jobs', 'panel'], Path(section_pucker_cli.__file__).resolve())]


def test_old_wrapper_still_materializes_its_own_recipe():
    run_python(r'''
import sys
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design import families
from tools.geometry import crowe_panel_cli as cli
cli.install(); d=DesignSpace.from_config(load_config(sys.argv[1])).seed
families.validate(d)
r=d.params['grid']['rows']
assert r['type']=='crowe_panel' and r['implementation_sha256']==cli.implementation_digest()
''', OLD)
