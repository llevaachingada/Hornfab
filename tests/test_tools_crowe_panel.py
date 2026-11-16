"""CPU checks for the source-constrained panel geometry and its adapter."""
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.spatial import cKDTree

from hornlab_search.config import load_config
from hornlab_search.design.generators.grid import check_self_approach
from tools.geometry import crowe_panel as panel

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'examples/typologies/rolled_rect_2026-11-15/rr__crowe_panel_es600_v7.yaml'

@pytest.fixture(scope='module')
def inputs():
    cfg = load_config(CONFIG)
    shape = {k: cfg.seed_params['g_'+k] for k in panel.SHAPE_KEYS-{'n_phi','n_s','wall_thickness_mm'}}
    shape.update({k: cfg.generator[k] for k in ('n_phi','n_s','wall_thickness_mm')})
    return shape, cfg.brief


def test_reference_meridians_reproduce_manual_landmarks(inputs):
    shape, brief = inputs
    ref = panel.reference()
    h, v = panel.section_profiles(shape, brief['driver'])
    for actual, name in ((h, 'horizontal_mm'), (v, 'vertical_mm')):
        measured = np.asarray(ref[name], float).copy()
        # 17.78 mm drawing exit is adapted to the 18.00 mm HF1440 exit.
        scale = ((shape['width_mm'] if name.startswith('horizontal') else shape['height_mm'])/2-18) / ((ref['reference_width_mm'] if name.startswith('horizontal') else ref['reference_height_mm'])/2-17.78)
        measured[:,0] = 18+(measured[:,0]-17.78)*scale
        distances = cKDTree(actual).query(measured)[0]
        assert np.max(distances) < .05


def test_surface_axis_cuts_track_measured_sections(inputs):
    shape, brief = inputs
    points = panel.surface_at(shape, brief['driver'], np.linspace(0, 1, 8193), [0, math.pi/2])
    h, v = panel.section_profiles(shape, brief['driver'])
    for axis, ref in ((0,h), (1,v)):
        measured = ref[ref[:,1] > shape['throat_blend_mm']+2]
        cut = points[axis][:,[axis,2]]
        dist = cKDTree(cut).query(measured)[0]
        assert np.quantile(dist, .99) < .6


def test_round_throat_and_isotropic_exit_slope(inputs):
    shape, brief = inputs
    phis = np.linspace(0, math.pi/2, 41)
    p = panel.surface_at(shape, brief['driver'], [0, 1e-6], phis)
    radius = np.hypot(p[...,0], p[...,1])
    np.testing.assert_allclose(radius[:,0],18.,atol=1e-10)
    np.testing.assert_allclose((radius[:,1]-radius[:,0])/p[:,1,2], math.tan(math.radians(2)), atol=1e-7)


def test_sweep_intersection_domain_and_boundaries(inputs):
    shape, brief = inputs
    station,v,joint,pivot,crown,start = panel._sweep(shape, brief['driver'])
    assert pivot>0 and np.all(np.diff(station)>0) and start < shape['throat_blend_mm']
    assert np.isfinite(joint).all() and np.isfinite(crown).all()
    # The held throat joint is intentionally masked until the inverse exists.
    mask = v[:,1] >= start+1e-6
    residual = joint[:,0]**2+(joint[:,1]+pivot)**2-(v[:,1]+pivot)**2
    assert np.max(np.abs(residual[mask])) < .1
    p = panel.surface_at(shape, brief['driver'], np.linspace(0,1,301), [0, math.pi/2])
    assert np.max(np.abs(p[0,:,1])) == 0 and np.max(np.abs(p[1,:,0])) == 0


def test_crown_alters_transverse_surface_preserving_vertical_axis(inputs):
    shape, brief = inputs
    stations=np.linspace(.1,.95,150)
    phi=[.4, math.pi/2]
    base=panel.surface_at({**shape,'crown_mm':0.},brief['driver'],stations,phi)
    crown=panel.surface_at(shape,brief['driver'],stations,phi)
    np.testing.assert_allclose(base[1],crown[1],atol=1e-9)
    assert np.max(np.linalg.norm(base[0]-crown[0],axis=-1)) > 1.


def test_join_and_refined_grid_are_finite(inputs):
    shape, brief=inputs
    p=panel.surface_at(shape,brief['driver'],np.linspace(.1,.95,150),np.linspace(0,math.pi/2,401))
    d=np.diff(p,axis=0)
    assert np.isfinite(d).all()
    assert np.max(np.linalg.norm(d,axis=2)) < 5.
    coarse,_=panel.make_grid(shape,brief)
    fine,_=panel.make_grid({**shape,'n_phi':2*(int(shape['n_phi'])-1)+1,'n_s':2*int(shape['n_s'])},brief)
    np.testing.assert_allclose(coarse,fine[::2,::2],atol=.03)
    outer=panel.outer_points(coarse,shape)
    assert np.isfinite(outer).all()
    for surface in (coarse,outer):
        normal=np.cross(np.gradient(surface,axis=0),np.gradient(surface,axis=1))
        assert np.min(np.linalg.norm(normal,axis=2)) > 1e-8
    check_self_approach(coarse,outer,shape['wall_thickness_mm'])


def test_stock_rejection_and_fresh_adapter_digest():
    code = r'''
from pathlib import Path
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design import families
from tools.geometry import crowe_panel_cli as cli
cfg=load_config(r"%s")
try: DesignSpace.from_config(cfg)
except Exception: pass
else: raise AssertionError("stock accepted experimental type")
cli.install()
d=DesignSpace.from_config(cfg).seed
families.validate(d)
r=d.params['grid']['rows']
assert r['type']=='crowe_panel' and r['implementation_sha256']==cli.implementation_digest()
assert cli.crowe_panel.REFERENCE.is_file()
import tempfile
with tempfile.TemporaryDirectory() as directory:
    replacement=Path(directory)/'reference.yaml'
    replacement.write_bytes(cli.crowe_panel.REFERENCE.read_bytes()+b'\n# changed\n')
    old=cli.implementation_digest()
    cli.crowe_panel.REFERENCE=replacement
    assert cli.implementation_digest()!=old
''' % CONFIG
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0, result.stdout+result.stderr


def test_explicit_outerbody_only_for_new_typology_in_fresh_process():
    code=r'''
import numpy as np
from hornlab_search.mesh import grid_build
from tools.geometry import crowe_panel_cli as cli
calls=[]
def original(block, *, enclosure=None): calls.append(block); return block
# install captures this stand-in, so no mesher or grid I/O runs
grid_build._resolve_grid=original
cli.install()
cli.crowe_panel.outer_points=lambda points, shape: np.full_like(points,42)
p=np.zeros((2,2,3)); shape={}
grid_build._resolve_grid({'inner_points':p,'meta':{'construction_label':'other'}})
grid_build._resolve_grid({'inner_points':p,'meta':{'construction_label':cli.crowe_panel.SCHEMA,'shape':shape}})
assert 'outer_points' not in calls[0]
assert np.all(calls[1]['outer_points']==42)
try: grid_build._resolve_grid({'inner_points':p,'meta':{'construction_label':cli.crowe_panel.SCHEMA,'shape':shape}},enclosure={})
except ValueError: pass
else: raise AssertionError('enclosure accepted')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0, result.stdout+result.stderr


def test_verify_night_routes_panel_wrapper(monkeypatch):
    from tools.geometry import crowe_panel_cli, verify_rolled_rect_night
    monkeypatch.setattr(verify_rolled_rect_night,'WRAPPER',verify_rolled_rect_night.WRAPPER)
    calls=[]
    monkeypatch.setattr(verify_rolled_rect_night,'main',lambda args: calls.append((args,verify_rolled_rect_night.WRAPPER)) or 0)
    assert crowe_panel_cli.main(['verify-night','--night','demo','--jobs','panel'])==0
    assert calls==[(['--night','demo','--jobs','panel'],Path(crowe_panel_cli.__file__).resolve())]
