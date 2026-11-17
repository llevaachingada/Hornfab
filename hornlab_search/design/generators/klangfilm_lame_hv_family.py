"""Versioned Klangfilm-Lame H/V throat-core adapter (Phase A).

The implementation digest binds this adapter, the frozen H/V kernel, the frozen legacy
parent kernel, the frozen cap math and the shell mesher to every saved recipe. This is a
CPU geometry interface, not an acoustic-readiness claim.

Frozen from tools/geometry/klangfilm_lame_hv.py SHA256
cbb23cc02d9b5d135e1ec46b4d0f3fdac68f8120c313b1a8ffe8e360672bea02.
The kernel imports were adapted to the frozen package-local parent and cap modules.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np
import scipy

from . import _klangfilm_lame_hv_v1 as kernel, _klangfilm_lame_v1 as parent
from . import _lame_cap_v1 as lame_cap
from . import lame_shell
from .registry import GeneratorError

KIND = 'klangfilm_lame_hv_cd'
SCHEMA = 'klangfilm-lame-hv-canonical-v1'
GRID_KEYS = frozenset({'n_phi', 'n_s', 'wall_thickness_mm'})
SPEC_KEYS = frozenset({'name', 'rows', 'n_phi', 'n_s', 'wall_thickness_mm', 'span', 'knobs',
                       'size_policy'})

#: Versioned size policy for this family only. ``enforce`` is the legacy behaviour (envelope
#: violation = invalid design). ``report_only`` keeps the geometry materialisable and records the
#: violation in ``meta`` so an enlarged-envelope discovery study can be reported honestly; the
#: search-layer envelope gate and the brief are NOT bypassed by it.
SIZE_POLICIES = ('enforce', 'report_only')

#: Phase A knobs whose effect requires a non-zero ``cd_core_blend``.
_DORMANT_KEYS = ('g_theta_h0_deg', 'g_theta_v0_deg', 'g_h_mid_gain_mm',
                 'g_v_mid_gain_mm', 'g_core_join_fraction')


def is_family_spec(spec):
    return isinstance(spec, dict) and isinstance(spec.get('rows'), dict) and spec['rows'].get('type') == KIND


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(kernel.__file__), Path(parent.__file__),
                 Path(lame_cap.__file__), Path(lame_shell.__file__)):
        data = path.read_bytes().replace(b'\r\n', b'\n')
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    digest.update(f'numpy={np.__version__};scipy={scipy.__version__}'.encode())
    return digest.hexdigest()


def _driver(driver):
    if not isinstance(driver, dict):
        raise GeneratorError('K family requires an explicit driver')
    try:
        out = {k: float(driver[k]) for k in ('exit_radius_mm', 'exit_angle_deg')}
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError('driver radius and exit angle are required') from exc
    if not all(math.isfinite(v) for v in out.values()) or out['exit_radius_mm'] <= 0 or not 0 < out['exit_angle_deg'] < 45:
        raise GeneratorError('invalid driver radius or exit angle')
    return out


def _shape(spec, knobs, *, require_digest=False, brief=None):
    if not is_family_spec(spec) or set(spec) - SPEC_KEYS:
        raise GeneratorError('invalid canonical K specification')
    rows = spec['rows']
    if set(rows) - {'type', 'schema', 'implementation_sha256', 'driver'}:
        raise GeneratorError('unknown canonical K rows metadata')
    if spec.get('span', 'quarter') != 'quarter':
        raise GeneratorError('canonical K requires quarter symmetry')
    if spec.get('size_policy', 'enforce') not in SIZE_POLICIES:
        raise GeneratorError(f"size_policy must be one of {list(SIZE_POLICIES)}")
    if require_digest or 'implementation_sha256' in rows or 'schema' in rows or 'driver' in rows:
        if rows.get('schema') != SCHEMA or rows.get('implementation_sha256') != implementation_digest():
            raise GeneratorError('canonical K schema or implementation differs from saved recipe')
        saved = _driver(rows.get('driver'))
        if brief is not None and saved != _driver(brief.get('driver')):
            raise GeneratorError('canonical K driver differs from saved recipe')
    keys = kernel.SHAPE_KEYS - GRID_KEYS
    expected = {'g_' + k for k in keys}
    if not isinstance(knobs, dict) or set(knobs) != expected:
        raise GeneratorError(f'canonical K knob mismatch: expected {sorted(expected)}')
    try:
        shape = {k: knobs['g_' + k] for k in keys}
        shape.update({k: spec[k] for k in GRID_KEYS})
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in shape.values()):
            raise ValueError('shape values must be finite numbers')
        kernel.validate_shape(shape)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise GeneratorError(f'canonical K shape: {exc}') from exc
    return shape


def resolve_grid(block, brief):
    """Regenerate saved inner and sampled normal-offset shell from a bound recipe."""
    driver = _driver((brief or {}).get('driver'))
    shape = _shape(block, block.get('knobs'), require_digest=True, brief=brief)
    if brief.get('mounting'):
        raise GeneratorError('canonical K explicit body cannot use a mounting enclosure')
    try:
        inner, meta = kernel.make_grid(shape, {'driver': driver})
        outer, metrics = lame_shell.offset_quarter_surface(inner, shape['wall_thickness_mm'])
        from . import grid
        grid.check_self_approach(inner, outer, shape['wall_thickness_mm'])
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f'canonical K geometry: {exc}') from exc
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    extents = (2*np.max(abs(both[:, 0])), 2*np.max(abs(both[:, 1])), np.ptp(both[:, 2]))
    policy = block.get('size_policy', 'enforce')
    if policy not in SIZE_POLICIES:
        raise GeneratorError(f"size_policy must be one of {list(SIZE_POLICIES)}")
    violations = []
    for actual, key in zip(extents, ('max_mouth_w_mm', 'max_mouth_h_mm', 'max_depth_mm')):
        limit = (brief.get('envelope') or {}).get(key)
        if limit is not None and actual > float(limit):
            if policy == 'enforce':
                raise GeneratorError(f'invalid_envelope: {key} {actual:.3f} exceeds {limit}')
            violations.append({'key': key, 'actual_mm': float(actual), 'limit_mm': float(limit)})
    meta.update(schema=SCHEMA, implementation_sha256=implementation_digest(), driver=driver,
                outer_offset='sampled 3D surface normal', shell_metrics=metrics,
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]), x_span_mm=float(extents[2]),
                size_policy=policy, envelope_violations=violations, envelope_ok=not violations)
    return {'inner_points': inner, 'outer_points': outer, 'meta': meta}


def design_params(spec, knobs, brief):
    _shape(spec, knobs, brief=brief)
    rows = {**copy.deepcopy(spec['rows']), 'schema': SCHEMA,
            'implementation_sha256': implementation_digest(), 'driver': _driver(brief.get('driver'))}
    block = {'rows': rows, **{k: spec[k] for k in GRID_KEYS}, 'knobs': dict(knobs), 'span': 'quarter'}
    if 'size_policy' in spec:
        block['size_policy'] = spec['size_policy']
    resolve_grid(block, brief)
    return {'grid': block}


def validate_grid_params(block):
    _shape(block, block.get('knobs'), require_digest=True)


def validate_search_config(spec, seed, bounds, brief):
    if spec.get('size_policy', 'enforce') not in SIZE_POLICIES:
        raise GeneratorError(f"size_policy must be one of {list(SIZE_POLICIES)}")
    _shape(spec, seed, brief=brief)
    expected = {'g_' + k for k in kernel.SHAPE_KEYS - GRID_KEYS}
    if set(bounds) != expected:
        raise GeneratorError('every canonical K knob needs an explicit matching bound')
    for key in expected:
        b, value = bounds[key], seed[key]
        if not all(math.isfinite(v) for v in (b.lo, b.hi, value)) or not b.lo <= value <= b.hi:
            raise GeneratorError(f'{key}: invalid bounds or seed')
        if not b.search and not b.lo == b.hi == value:
            raise GeneratorError(f'{key}: fixed bound must equal its seed')
        if b.log:
            raise GeneratorError('canonical K knobs require linear physical bounds')
        for endpoint in (b.lo, b.hi):
            _shape(spec, {**seed, key: endpoint}, brief=brief)
    # Phase A dormancy: the new H/V knobs are inert unless ``cd_core_blend`` is actually non-zero.
    blend = bounds['g_cd_core_blend']
    blend_fixed_zero = (not blend.search) and blend.lo == blend.hi == 0.0
    if blend_fixed_zero:
        for key in _DORMANT_KEYS:
            b, value = bounds[key], seed[key]
            if b.search or not b.lo == b.hi == value:
                raise GeneratorError('phase A knobs are inert when cd_core_blend is fixed at 0')
    if blend.search and blend.lo <= 0.0 < blend.hi:
        for key in _DORMANT_KEYS:
            if bounds[key].search:
                raise GeneratorError('inert lower bound: cd_core_blend can reach 0 while phase A knobs are searched')
    # report_only keeps an over-envelope geometry reportable, but it is not a licence to optimise past
    # the manufacturing envelope: the search layer and the brief still enforce it. An enlarged-envelope
    # study needs a widened brief, not this flag.
    if spec.get('size_policy') == 'report_only' and any(b.search for b in bounds.values()):
        raise GeneratorError('size_policy report_only is a geometry/diagnostics lane; an enlarged-envelope '
                             'search requires a widened brief envelope')
