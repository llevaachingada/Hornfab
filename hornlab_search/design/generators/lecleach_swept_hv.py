"""Experimental flat-section Le Cleac'h H/V point-grid kernel, CPU only.

This is not a registered or solver-ready generator.  Flat cross-sectional
area, rather than the parent's curved wavefront area, is preserved before
axial sweep.  Lip and axial deformation are experimental and require further physical validation.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import brentq

from . import profiles, section_lame

SCHEMA = 'lecleach-swept-hv-prototype-v1'
KEYS = frozenset({'g_fc_hz', 'g_T', 'g_stop_deg', 'g_ar_m', 'g_ar_p',
                  'g_lame_p_mouth', 'g_lip_radius_mm', 'g_rim_sweep_mm',
                  'g_axial_length_factor'})


def make_grid(params, *, throat_radius_mm, throat_half_angle_deg, n_phi=25,
              n_s=96, dl_mm=1.0):
    """Return (quarter grid, metadata); grid shape is (n_phi, n_s+1, 3).

    Sweep affects the whole parent, with the quintic gate defined over its
    actual meridian arc length.  This prototype does not construct a shell or
    certify intersections, curvature, mesh quality, or acoustic suitability.
    """
    if set(params) != KEYS:
        raise ValueError(f'parameter keys: missing={sorted(KEYS-set(params))}, unknown={sorted(set(params)-KEYS)}')
    vals = {}
    for key, value in params.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite numeric')
        vals[key] = float(value)
    p = vals
    if not (p['g_fc_hz'] > 0 and 0 <= p['g_T'] and p['g_ar_m'] >= 1 and
            1 <= p['g_ar_p'] <= 2 and 2 <= p['g_lame_p_mouth'] <= 6 and
            0 <= p['g_rim_sweep_mm'] <= 60):
        raise ValueError('invalid parent or extension parameter')
    if not 0 <= p['g_lip_radius_mm'] <= 25:
        raise ValueError('lip radius must be in [0, 25] mm')
    if not 1 <= p['g_axial_length_factor'] <= 1.35:
        raise ValueError('axial length factor must be in [1, 1.35]')
    if isinstance(n_phi, bool) or isinstance(n_s, bool) or int(n_phi) != n_phi or int(n_s) != n_s or n_phi < 3 or n_s < 8:
        raise ValueError('n_phi >= 3 and n_s >= 8 must be integers')
    z, r, parent_angle, parent_meta = profiles.lecleach_exact(throat_radius_mm, p['g_fc_hz'], p['g_T'],
                                                    throat_half_angle_deg, p['g_stop_deg'], dl_mm=dl_mm)
    z, r = np.asarray(z), np.asarray(r)
    if not np.all(np.isfinite(z)) or not np.all(np.isfinite(r)) or np.any(r <= 0):
        raise ValueError('invalid parent contour')
    arc = np.r_[0., np.cumsum(np.hypot(np.diff(z), np.diff(r)))]
    if arc[-1] <= 0 or np.any(np.diff(arc) <= 0):
        raise ValueError('degenerate parent contour')
    s = np.linspace(0., 1., int(n_s) + 1)
    zi, ri = np.interp(s * arc[-1], arc, z), np.interp(s * arc[-1], arc, r)
    gate = section_lame.smootherstep(s)
    raw_depth = float(np.ptp(zi))
    if raw_depth <= 0:
        raise ValueError('degenerate parent depth')
    delta = 0.0
    if p['g_axial_length_factor'] > 1:
        target = raw_depth * p['g_axial_length_factor']
        def depth_error(d):
            return float(np.ptp(zi + d * gate)) - target
        upper = max(raw_depth, 1.0)
        for _ in range(20):
            if depth_error(upper) >= 0:
                break
            upper *= 2
        else:
            raise ValueError('cannot bracket axial depth warp')
        delta = brentq(depth_error, 0, upper)
        zi = zi + delta * gate
    q = 1 + (p['g_ar_m'] - 1) * gate ** p['g_ar_p']
    exponent = 2 + (p['g_lame_p_mouth'] - 2) * gate
    phi = np.linspace(0, np.pi / 2, int(n_phi))
    points = np.empty((int(n_phi), int(n_s) + 1, 3))
    for i in range(len(s)):
        a, b = section_lame.flat_area_axes(math.pi * ri[i] ** 2, q[i], exponent[i])
        rho = section_lame.polar_radius(phi, a, b, exponent[i])
        points[:, i, 0] = rho * np.cos(phi)
        points[:, i, 1] = rho * np.sin(phi)
        points[:, i, 2] = zi[i] - p['g_rim_sweep_mm'] * np.cos(phi)**2 * gate[i]
    # The march endpoint angle is the direction of its last discrete segment,
    # not an independently established derivative of continuous Fourcade geometry.
    # At the endpoint the aspect, exponent, warp and sweep gates have zero
    # derivative. Fixed-ray radius is therefore a constant multiple of the
    # parent radius to first order. Join a circular arc to that one-sided tangent.
    lip_radius = p['g_lip_radius_mm']
    if lip_radius:
        # Undo sweep before constructing the lip; sweep is applied once below.
        points[:, :, 2] += p['g_rim_sweep_mm'] * np.cos(phi)[:, None]**2 * gate
        end = points[:, -1, :].copy()
        theta = math.radians(float(parent_angle[-1]))
        radial_scale = np.hypot(end[:, 0], end[:, 1]) / ri[-1]
        radial_component = radial_scale * math.sin(theta)
        axial_component = np.full_like(radial_component, math.cos(theta))
        lengths = np.hypot(radial_component, axial_component)
        if np.any(lengths <= 1e-9):
            raise ValueError('degenerate terminal tangent')
        tangent = np.column_stack((radial_component * np.cos(phi),
                                   radial_component * np.sin(phi), axial_component)) / lengths[:, None]
        # A meridian normal rotates the axial/radial tangent toward the rim.
        radial = np.c_[np.cos(phi), np.sin(phi), np.zeros_like(phi)]
        tr = np.sum(tangent * radial, axis=1)
        tz = tangent[:, 2]
        normal = tz[:, None] * radial - tr[:, None] * np.array([0., 0., 1.])
        t = np.linspace(0, np.pi / 4, 9)[1:]
        extension = end[:, None, :] + lip_radius * (np.sin(t)[None, :, None] * tangent[:, None, :] +
                    (1 - np.cos(t))[None, :, None] * normal[:, None, :])
        if np.any(np.sum(extension * radial[:, None, :], axis=2) <= 0):
            raise ValueError('lip crosses axis')
        points = np.concatenate((points, extension), axis=1)
        # The sweep reaches its specified value at the parent rim and holds
        # through the lip. This avoids a second independent sweep operator.
        sweep_gate = np.r_[gate, np.ones(len(t))]
        points[:, :, 2] -= p['g_rim_sweep_mm'] * np.cos(phi)[:, None]**2 * sweep_gate
    points[0, :, 1] = 0
    points[-1, :, 0] = 0
    if not np.all(np.isfinite(points)):
        raise ValueError('nonfinite surface')
    metadata = {'schema': SCHEMA, 'area_mode': 'flat_section_parent',
                'sweep_scope': 'entire_parent_arclength_held_through_lip', 'params': dict(p),
                'axial_warp_delta_mm': delta, 'parent_depth_mm': raw_depth,
                'lip_wrap_deg': 45.0 if lip_radius else 0.0,
                'lip_continuity': 'tangent_to_discrete_march_interpolant_unvalidated' if lip_radius else 'none',
                'width_mm': float(2 * points[:, :, 0].max()),
                'height_mm': float(2 * points[:, :, 1].max()),
                'depth_mm': float(np.ptp(points[:, :, 2])),
                'parent_meta': parent_meta, 'shell_and_validity': 'not_checked'}
    return points, metadata

# Versioned adapter; the prototype make_grid above remains unchanged for archived renders.
PRODUCTION_SCHEMA = 'lecleach-swept-hv-v1'
ROW_FIELDS = {'type': 'lecleach_swept_hv', 'schema': PRODUCTION_SCHEMA,
              'area_mode': 'flat_section_parent', 'aspect_progression': 'quintic',
              'lame_progression': 'quintic', 'lip_model': 'tangent_arc'}


def is_family_spec(spec):
    return isinstance(spec, dict) and isinstance(spec.get('rows'), dict) and spec['rows'].get('type') == ROW_FIELDS['type']


def implementation_digest():
    """Hash all local geometry dependencies and numerical-library versions."""
    import hashlib
    from pathlib import Path
    import scipy
    from hornlab_search import constants
    from . import lame_shell
    h = hashlib.sha256()
    for path in (Path(__file__), Path(profiles.__file__), Path(section_lame.__file__),
                 Path(lame_shell.__file__), Path(constants.__file__)):
        data = path.read_bytes().replace(b'\r\n', b'\n')
        h.update(len(data).to_bytes(8, 'big'))
        h.update(data)
    h.update(f'numpy={np.__version__};scipy={scipy.__version__}'.encode())
    return h.hexdigest()


def _driver(brief):
    from .registry import GeneratorError
    try:
        driver = brief['driver']
        values = {k: float(driver[k]) for k in ('exit_radius_mm', 'exit_angle_deg')}
        if any(isinstance(driver[k], bool) for k in values) or not all(math.isfinite(v) for v in values.values()):
            raise ValueError('driver must be finite numeric')
        if values['exit_radius_mm'] <= 0 or not 0 < values['exit_angle_deg'] < 45:
            raise ValueError('invalid source radius or exit angle')
        return values
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError(f'lecleach swept source: {exc}') from exc


def _check(spec, knobs, *, saved=False, brief=None):
    from .registry import GeneratorError
    if not is_family_spec(spec) or set(spec) - {'name', 'rows', 'n_phi', 'n_s', 'span', 'wall_thickness_mm', 'knobs'}:
        raise GeneratorError('invalid lecleach swept grid specification')
    rows = spec['rows']
    if set(rows) - (set(ROW_FIELDS) | {'implementation_sha256', 'driver'}):
        raise GeneratorError('unknown lecleach swept rows field')
    if any(rows.get(k) != v for k, v in ROW_FIELDS.items()):
        raise GeneratorError('lecleach swept rows must specify the exact v1 construction fields')
    if spec.get('span', 'quarter') != 'quarter':
        raise GeneratorError('lecleach swept requires quarter symmetry')
    if not isinstance(knobs, dict) or set(knobs) != KEYS:
        raise GeneratorError(f'lecleach swept requires exactly {sorted(KEYS)}')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in knobs.values()):
        raise GeneratorError('lecleach swept knobs must be finite numeric values')
    if saved or 'implementation_sha256' in rows:
        if rows.get('implementation_sha256') != implementation_digest():
            raise GeneratorError('lecleach swept implementation differs from saved recipe')
        if not isinstance(rows.get('driver'), dict) or set(rows['driver']) != {'exit_radius_mm', 'exit_angle_deg'}:
            raise GeneratorError('saved lecleach swept driver missing or malformed')
        if rows['driver'] != _driver({'driver': rows['driver']}):
            raise GeneratorError('saved lecleach swept driver is not canonical')
        if brief is not None and rows['driver'] != _driver(brief):
            raise GeneratorError('lecleach swept driver differs from saved recipe')
    for key, minimum in (('n_phi', 13), ('n_s', 8)):
        v = spec.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
            raise GeneratorError(f'{key} must be an integer >= {minimum}')
    t = spec.get('wall_thickness_mm')
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 0.5 <= t <= 12:
        raise GeneratorError('wall_thickness_mm must be in [0.5, 12]')


def resolve_grid(block, brief):
    from .registry import GeneratorError
    from . import lame_shell, grid
    _check(block, block.get('knobs'), saved=True, brief=brief)
    if brief.get('mounting'):
        raise GeneratorError('lecleach swept explicit shell cannot use a mounting enclosure')
    driver = _driver(brief)
    try:
        inner, meta = make_grid(block['knobs'], throat_radius_mm=driver['exit_radius_mm'],
                                throat_half_angle_deg=driver['exit_angle_deg'],
                                n_phi=block['n_phi'], n_s=block['n_s'])
        outer, diagnostics = lame_shell.offset_quarter_surface(inner, block['wall_thickness_mm'])
        grid.check_self_approach(inner, outer, block['wall_thickness_mm'])
    except (ValueError, TypeError, OverflowError) as exc:
        raise GeneratorError(f'lecleach swept geometry: {exc}') from exc
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    extents = (2 * np.max(np.abs(both[:, 0])), 2 * np.max(np.abs(both[:, 1])), np.ptp(both[:, 2]))
    for actual, key in zip(extents, ('max_mouth_w_mm', 'max_mouth_h_mm', 'max_depth_mm')):
        limit = (brief.get('envelope') or {}).get(key)
        if limit is not None and actual > float(limit):
            raise GeneratorError(f'invalid_envelope: {key} {actual:.3f} exceeds {limit}')
    meta.update(schema=PRODUCTION_SCHEMA, rows_type=ROW_FIELDS['type'], driver=driver,
                implementation_sha256=implementation_digest(), shell_and_validity=diagnostics,
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]), x_span_mm=float(extents[2]),
                source_auto_angle_deg=driver['exit_angle_deg'])
    return {'inner_points': inner, 'outer_points': outer, 'meta': meta}


def design_params(spec, knobs, brief):
    _check(spec, knobs, brief=brief)
    block = {k: spec[k] for k in ('n_phi', 'n_s', 'wall_thickness_mm')}
    block.update(rows={**ROW_FIELDS, 'implementation_sha256': implementation_digest(), 'driver': _driver(brief)},
                 span='quarter', knobs=dict(knobs))
    resolve_grid(block, brief)
    return {'grid': block}


def validate_grid_params(block):
    _check(block, block.get('knobs'), saved=True)


def validate_search_config(spec, seed, bounds, brief):
    """Validate independent knob bounds; this is not a geometry validity certificate."""
    from .registry import GeneratorError
    _check(spec, seed, brief=brief)
    driver = _driver(brief)
    if not isinstance(bounds, dict) or set(bounds) != KEYS:
        raise GeneratorError('every lecleach swept knob needs an explicit matching bound')
    for key in sorted(KEYS):
        b, value = bounds[key], seed[key]
        try:
            lo, hi = float(b.lo), float(b.hi)
            if isinstance(b.lo, bool) or isinstance(b.hi, bool) or not all(math.isfinite(v) for v in (lo, hi)):
                raise ValueError('bounds must be finite numeric values')
            if not lo <= value <= hi:
                raise ValueError('seed outside bounds')
            if not b.search and not lo == hi == value:
                raise ValueError('fixed bound must equal its seed')
            if b.search and lo == hi:
                raise ValueError('searched bound must have positive width')
            if b.log:
                raise ValueError('bounds must use linear physical units')
            # Use the same parent and parameter validation as materialization;
            # endpoint checks do not prove all combinations valid.
            for endpoint in (lo, hi):
                make_grid({**seed, key: endpoint}, throat_radius_mm=driver['exit_radius_mm'],
                          throat_half_angle_deg=driver['exit_angle_deg'],
                          n_phi=spec['n_phi'], n_s=spec['n_s'])
        except (AttributeError, TypeError, ValueError, OverflowError) as exc:
            raise GeneratorError(f'{key}: invalid search bound: {exc}') from exc
    if bounds['g_ar_p'].search and bounds['g_ar_m'].lo <= 1:
        raise GeneratorError('g_ar_p is dormant when g_ar_m can equal 1; pin progression or exclude round aspect')
