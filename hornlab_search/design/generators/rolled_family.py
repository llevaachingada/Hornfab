"""Canonical, versioned rolled-family geometry shared by all optimizers.

The frozen research kernels remain reproducible. This layer names radial inward
and axial relief separately and binds the same inner/outer geometry to the recipe.
It generates points only; HornLab owns meshing, source closure and BEM.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
import numpy as np
from . import _rolled_rect_v1 as rolled_rect, _crowe_section_v2 as crowe_panel
from .registry import GeneratorError
from .. import throat_hv

KINDS = ('rolled_family_rect_v1', 'rolled_family_section_v1')
MODES = ('smooth', 'radial', 'axial', 'hybrid')
SCHEMA = 'rolled-family-master-v1'
RELIEF_KEYS = frozenset({'inward_h_mm', 'inward_v_mm', 'axial_h_mm', 'axial_v_mm',
                         'relief_start_s', 'relief_peak_s', 'relief_end_s'})
GRID_KEYS = frozenset({'n_phi', 'n_s', 'wall_thickness_mm'})
SPEC_KEYS = frozenset({'name', 'rows', 'n_phi', 'n_s', 'wall_thickness_mm', 'span', 'knobs'})


def is_family_spec(spec):
    return (isinstance(spec, dict) and isinstance(spec.get('rows'), dict)
            and spec['rows'].get('type') in KINDS)


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(rolled_rect.__file__), Path(crowe_panel.__file__),
                 crowe_panel.REFERENCE):
        data = path.read_bytes().replace(b'\r\n', b'\n')
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


def shape_keys(kind):
    if kind == KINDS[0]:
        parent = rolled_rect.SHAPE_KEYS-{'pucker_h_mm', 'pucker_v_mm', 'pucker_start_deg'}
    elif kind == KINDS[1]:
        parent = crowe_panel.SHAPE_KEYS
    else:
        raise GeneratorError(f'unknown rolled-family type: {kind!r}')
    return parent | RELIEF_KEYS


def _driver(driver):
    if not isinstance(driver, dict):
        raise GeneratorError('rolled family requires an explicit driver')
    try:
        result = {k: float(driver[k]) for k in ('exit_radius_mm', 'exit_angle_deg')}
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError('driver radius and exit angle are required') from exc
    if (not all(math.isfinite(x) for x in result.values()) or result['exit_radius_mm'] <= 0
            or not 0 < result['exit_angle_deg'] < 45):
        raise GeneratorError('need positive radius and exit angle in (0,45)')
    return result


def _parent(shape, kind):
    if kind == KINDS[0]:
        result = {k: shape[k] for k in rolled_rect.SHAPE_KEYS if k in shape}
        # These unused legacy slots are explicit derived neutral values.
        result.update(pucker_h_mm=0., pucker_v_mm=0., pucker_start_deg=shape['rect_turn_deg'])
        return rolled_rect, result
    return crowe_panel, {k: shape[k] for k in crowe_panel.SHAPE_KEYS}


def _throat_knobs(knobs):
    """Shared near-throat H/V block read from the g_-prefixed knobs; absent keys stay None."""
    if not isinstance(knobs, dict):
        return throat_hv.parse({})
    present = {k: knobs[k] for k in ('g_'+x for x in throat_hv.KEYS) if knobs.get(k) is not None}
    return throat_hv.parse(present, prefix='g_')


def _throat_window_start(shape, throat):
    return throat['hv_onset_frac'] if throat['hv_onset_frac'] is not None else shape['relief_start_s']


def _shape(spec, knobs, *, require_digest=False, brief=None):
    if not is_family_spec(spec) or set(spec)-SPEC_KEYS:
        raise GeneratorError('invalid rolled-family specification')
    rows = spec['rows']
    if set(rows)-{'type', 'mode', 'schema', 'implementation_sha256', 'driver'}:
        raise GeneratorError('unknown rolled-family rows metadata')
    if spec.get('span', 'quarter') != 'quarter':
        raise GeneratorError('rolled family requires quarter symmetry')
    mode = rows.get('mode')
    if mode not in MODES:
        raise GeneratorError(f'explicit relief mode required, one of {MODES}')
    if require_digest or 'implementation_sha256' in rows:
        if rows.get('schema') != SCHEMA or rows.get('implementation_sha256') != implementation_digest():
            raise GeneratorError('rolled-family schema or implementation differs from saved recipe')
        saved_driver = _driver(rows.get('driver'))
        if brief is not None and saved_driver != _driver(brief.get('driver')):
            raise GeneratorError('rolled-family driver differs from saved recipe')
    kind = rows['type']
    try:
        throat = _throat_knobs(knobs)
    except throat_hv.ThroatHVError as exc:
        raise GeneratorError(f'rolled-family throat-HV block: {exc}') from exc
    if throat['throat_hv_ratio'] not in (None, 1.0):
        raise GeneratorError('throat_hv_ratio not supported by rolled family yet')
    onset_given = throat['hv_onset_frac'] is not None
    if onset_given and isinstance(knobs, dict) and 'g_relief_start_s' in knobs:
        raise GeneratorError('hv_onset_frac replaces relief_start_s; give only one')
    replaces_window = onset_given or throat['section_exp_ramp'] is not None
    given = {'g_'+k for k in throat_hv.KEYS
             if isinstance(knobs, dict) and knobs.get('g_'+k) is not None}
    base = shape_keys(kind)-GRID_KEYS
    if onset_given:
        base = base-{'relief_start_s'}
    expected = {'g_'+k for k in base} | given
    if not isinstance(knobs, dict) or set(knobs) != expected:
        raise GeneratorError(f'rolled-family knob mismatch: expected {sorted(expected)}')
    try:
        shape = {k: knobs['g_'+k] for k in base}
        shape.update({k: spec[k] for k in GRID_KEYS})
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
               for x in shape.values()):
            raise ValueError('all shape values must be finite numbers')
        kernel, parent = _parent(shape, kind)
        kernel.validate_shape(parent)
        if onset_given:
            if not 0 <= throat['hv_onset_frac'] < shape['relief_peak_s'] < shape['relief_end_s'] <= .96:
                raise ValueError('need 0 <= hv_onset_frac < peak < end <= .96')
        elif not .15 <= shape['relief_start_s'] < shape['relief_peak_s'] < shape['relief_end_s'] <= .96:
            raise ValueError('need .15 <= relief start < peak < end <= .96')
        for key in ('inward_h_mm', 'inward_v_mm'):
            if not 0 <= shape[key] <= .15*shape['height_mm']:
                raise ValueError('inward relief must be nonnegative and at most 15 percent of height')
        for key in ('axial_h_mm', 'axial_v_mm'):
            if abs(shape[key]) > .1*shape['depth_mm']:
                raise ValueError('axial relief exceeds ten percent of depth')
        radial = shape['inward_h_mm'] != 0 or shape['inward_v_mm'] != 0
        axial = shape['axial_h_mm'] != 0 or shape['axial_v_mm'] != 0
        if (mode in ('smooth', 'axial') and radial) or (mode in ('smooth', 'radial') and axial):
            raise ValueError('nonzero relief amplitude is inactive in the selected mode')
        if replaces_window and not (radial or axial):
            raise ValueError('hv_onset_frac/section_exp_ramp are inactive: relief and pucker amplitudes are zero')
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError(f'rolled-family shape: {exc}') from exc
    return shape, kernel, parent


def relief_window(shape, stations):
    s = np.asarray(stations, dtype=float)
    start, peak, end = (shape[k] for k in ('relief_start_s', 'relief_peak_s', 'relief_end_s'))
    return rolled_rect.smoothstep((s-start)/(peak-start))*rolled_rect.smoothstep((end-s)/(end-peak))


def _window(shape, stations, throat):
    """Relief weight; with the shared block the start is the ATH ramp, the end taper is unchanged."""
    if throat['hv_onset_frac'] is None and throat['section_exp_ramp'] is None:
        return relief_window(shape, stations)
    s = np.asarray(stations, dtype=float)
    end, peak = shape['relief_end_s'], shape['relief_peak_s']
    start_ramp = throat_hv.ath_ramp(s, _throat_window_start(shape, throat), throat['section_exp_ramp'])
    return start_ramp*rolled_rect.smoothstep((end-s)/(end-peak))


def _source_check(kernel, parent, driver):
    # Check the actual continuous base, not just its driver metadata. The relief
    # window is identically zero throughout this source neighbourhood.
    epsilon = 1e-7
    source = kernel.surface_at(parent, driver, [0., epsilon], np.linspace(0, math.pi/2, 9))
    radii = np.hypot(source[..., 0], source[..., 1])
    if np.max(abs(radii[:, 0]-driver['exit_radius_mm'])) > 1e-8:
        raise GeneratorError('source contour does not match the round driver')
    dz = source[:, 1, 2]-source[:, 0, 2]
    if np.any(dz <= 0):
        raise GeneratorError('source section does not advance from its coupling plane')
    slope = (radii[:, 1]-radii[:, 0])/dz
    if np.max(abs(slope-math.tan(math.radians(driver['exit_angle_deg'])))) > 1e-6:
        raise GeneratorError('source tangent does not match the driver')


def resolve_grid(block, brief):
    """Materialize the exact acoustic inner AND exterior surfaces, CPU only."""
    from . import grid
    driver = _driver((brief or {}).get('driver'))
    shape, kernel, parent = _shape(block, block.get('knobs'), require_digest=True, brief=brief)
    if brief.get('mounting'):
        raise GeneratorError('rolled-family explicit body cannot be combined with a mounting enclosure')
    _source_check(kernel, parent, driver)
    original, meta = kernel.make_grid(parent, {'driver': driver})
    if kernel is rolled_rect:
        stations = np.linspace(0, 1, original.shape[1])
        source_end = float(np.interp(parent['throat_turn_deg'], meta['turns_deg'], stations))
    else:
        stations = np.asarray(meta['stations'])
        ds, vertical, _, _, _, _ = kernel._sweep(parent, driver)
        ascending = np.arange(int(np.argmax(vertical[:, 1]))+1)
        source_end = float(np.interp(parent['throat_blend_mm'], vertical[ascending, 1], ds[ascending]))
    throat = _throat_knobs(block.get('knobs'))
    if _throat_window_start(shape, throat) <= source_end:
        raise GeneratorError('relief onset intersects the source matching region')
    w = _window(shape, stations, throat)
    if np.any(w[-2:] != 0):
        raise GeneratorError('relief reaches the exterior-body attachment normal')
    inner = original.copy()
    h, v = original[0, :, 0], original[-1, :, 1]
    psi = np.arctan2(original[..., 1]/v, original[..., 0]/h)
    rho = np.hypot(original[..., 0], original[..., 1])
    inward = (shape['inward_h_mm']*np.cos(psi)**2 + shape['inward_v_mm']*np.sin(psi)**2)
    inward = inward*np.cos(2*psi)**2*w
    if np.any(inward >= rho):
        raise GeneratorError('radial relief closes or crosses the horn centreline')
    if np.any(inward):
        factor = (rho-inward)/rho
        inner[..., 0] *= factor
        inner[..., 1] *= factor
    axial = (shape['axial_h_mm']*np.cos(psi)**2 + shape['axial_v_mm']*np.sin(psi)**2)
    if np.any(axial):
        inner[..., 2] += axial*np.cos(4*psi)*w
    # A local constriction before the parent's forward roll is not a usable flare.
    radial = np.hypot(inner[..., 0], inner[..., 1])
    for row in range(len(inner)):
        forward = int(np.argmax(original[row, :, 2]))
        if np.any(np.diff(radial[row, :forward+1]) < -1e-6):
            raise GeneratorError('relief creates a constriction before the mouth roll')
    outer = (grid.grid_outer_points(inner, shape['wall_thickness_mm']) if kernel is rolled_rect
             else kernel.outer_points(inner, parent))
    for name, sheet in [('inner', inner), ('outer', outer)]:
        if not np.isfinite(sheet).all():
            raise GeneratorError(f'nonfinite {name} surface')
        normal = np.cross(np.gradient(sheet, axis=0), np.gradient(sheet, axis=1))
        if np.min(np.linalg.norm(normal, axis=-1)) <= 1e-9:
            raise GeneratorError(f'degenerate {name} surface')
    grid.check_self_approach(inner, outer, shape['wall_thickness_mm'])
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    extents = [2*np.max(abs(both[:, 0])), 2*np.max(abs(both[:, 1])), np.ptp(both[:, 2])]
    for actual, key in zip(extents, ('max_mouth_w_mm', 'max_mouth_h_mm', 'max_depth_mm')):
        limit = (brief.get('envelope') or {}).get(key)
        if limit is not None and actual > float(limit):
            raise GeneratorError(f'invalid_envelope: {key} {actual:.3f} exceeds {limit}')
    if 'junction' in meta:
        meta['reference_junction'] = meta.pop('junction')
    meta.update(construction_label=SCHEMA, shape=dict(shape), relief_mode=block['rows']['mode'],
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]), x_span_mm=float(extents[2]),
                source_auto_angle_deg=driver['exit_angle_deg'], driver=driver,
                implementation_sha256=implementation_digest(), stations=stations.tolist())
    if throat_hv.is_active(throat):
        meta['throat_hv'] = {k: v for k, v in throat.items() if v is not None}
        meta['notes'] = [*meta.get('notes', []), throat_hv.STATUS['rolled']]
    return {'inner_points': inner, 'outer_points': outer, 'meta': meta}


def design_params(spec, knobs, brief):
    _shape(spec, knobs, brief=brief)
    rows = {**copy.deepcopy(spec['rows']), 'schema': SCHEMA,
            'implementation_sha256': implementation_digest(), 'driver': _driver(brief.get('driver'))}
    block = {'rows': rows, **{k: spec[k] for k in GRID_KEYS}, 'knobs': dict(knobs), 'span': 'quarter'}
    resolve_grid(block, brief)
    return {'grid': block}


def validate_grid_params(block):
    _shape(block, block.get('knobs'), require_digest=True)


def validate_search_config(spec, seed, bounds, brief):
    """Reject dormant dimensions, clipping and independently overlapping windows."""
    shape, _, _ = _shape(spec, seed, brief=brief)
    given = {'g_'+k for k in throat_hv.KEYS if isinstance(seed, dict) and seed.get('g_'+k) is not None}
    onset = 'g_hv_onset_frac' in given
    expected = {'g_'+k for k in shape_keys(spec['rows']['type'])-GRID_KEYS
                if not (onset and k == 'relief_start_s')} | given
    if set(bounds) != expected:
        raise GeneratorError('every rolled-family knob needs an explicit matching bound')
    intervals = {}
    for key in expected:
        b, value = bounds[key], seed[key]
        if not b.lo <= value <= b.hi:
            raise GeneratorError(f'{key}: seed outside its declared bounds')
        if not b.search and not b.lo == b.hi == value:
            raise GeneratorError(f'{key}: fixed bound must equal its seed')
        if b.log:
            raise GeneratorError('rolled-family knobs use explicit linear physical bounds')
        intervals[key[2:]] = (b.lo, b.hi)
        for endpoint in (b.lo, b.hi):
            _shape(spec, {**seed, key: endpoint}, brief=brief)
    mode = spec['rows']['mode']
    for prefix, active in [('inward', mode in ('radial', 'hybrid')), ('axial', mode in ('axial', 'hybrid'))]:
        if not active:
            for axis in ('h', 'v'):
                if intervals[f'{prefix}_{axis}_mm'] != (0., 0.):
                    raise GeneratorError(f'{prefix} relief is inactive in mode {mode}')
    start_key = 'hv_onset_frac' if onset else 'relief_start_s'
    start, peak, end = (intervals[k] for k in (start_key, 'relief_peak_s', 'relief_end_s'))
    if not start[1] < peak[0] or not peak[1] < end[0]:
        raise GeneratorError('independent relief position bounds overlap')
    position_search = any(bounds['g_'+k].search for k in (start_key, 'relief_peak_s', 'relief_end_s')
                          ) or ('g_section_exp_ramp' in given and bounds['g_section_exp_ramp'].search)
    strength_away_zero = any(lo > 0 or hi < 0 for k, (lo, hi) in intervals.items()
                             if k in ('inward_h_mm', 'inward_v_mm', 'axial_h_mm', 'axial_v_mm'))
    if position_search and not strength_away_zero:
        raise GeneratorError('relief position is dormant when all strengths can be zero; pin position')
    if intervals['width_mm'][0] <= intervals['height_mm'][1]:
        raise GeneratorError('width/height bounds permit a non-landscape shape')
    if intervals['height_mm'][0] <= 2*_driver(brief.get('driver'))['exit_radius_mm']:
        raise GeneratorError('height bound intersects the driver exit')
    if spec['rows']['type'] == KINDS[0]:
        if intervals['throat_turn_deg'][1] >= intervals['rect_turn_deg'][0]:
            raise GeneratorError('throat and rectangle transition bounds overlap')
