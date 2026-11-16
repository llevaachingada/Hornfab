"""Versioned Klangfilm-Lame grid adapter; legacy tool bridges remain independent.

The implementation digest binds the adapter and both research kernels to every
saved recipe. This is a CPU geometry interface, not an acoustic-readiness claim.

Frozen from tools/geometry/klangfilm_lame.py SHA256
728615be2a9f4070010f4cd4df448fc0ed322eaf74830fe3368083f0cd6d087e
and tools/geometry/lame_cap.py SHA256
9f0f06091d34fdb3b3499a1852432b74b3305aa6242c645c5452e7550484c9ae.
The kernel import was adapted to use the frozen package-local cap module.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np
import scipy

from . import _klangfilm_lame_v1 as kernel, _lame_cap_v1 as lame_cap
from . import lame_shell
from .registry import GeneratorError

KIND = 'klangfilm_lame_v1'
SCHEMA = 'klangfilm-lame-canonical-v1'
GRID_KEYS = frozenset({'n_phi', 'n_s', 'wall_thickness_mm'})
SPEC_KEYS = frozenset({'name', 'rows', 'n_phi', 'n_s', 'wall_thickness_mm', 'span', 'knobs'})


def is_family_spec(spec):
    return isinstance(spec, dict) and isinstance(spec.get('rows'), dict) and spec['rows'].get('type') == KIND


def implementation_digest():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(kernel.__file__), Path(lame_cap.__file__), Path(lame_shell.__file__)):
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
    for actual, key in zip(extents, ('max_mouth_w_mm', 'max_mouth_h_mm', 'max_depth_mm')):
        limit = (brief.get('envelope') or {}).get(key)
        if limit is not None and actual > float(limit):
            raise GeneratorError(f'invalid_envelope: {key} {actual:.3f} exceeds {limit}')
    meta.update(schema=SCHEMA, implementation_sha256=implementation_digest(), driver=driver,
                outer_offset='sampled 3D surface normal', shell_metrics=metrics,
                mouth_w_mm=float(extents[0]), mouth_h_mm=float(extents[1]), x_span_mm=float(extents[2]))
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
    # Entry angle is inert with zero source blend; no search of that dimension then.
    if bounds['g_entry_half_angle_deg'].search and bounds['g_source_blend_ratio'].lo <= 0:
        raise GeneratorError('entry angle is dormant when source blend can be zero')
