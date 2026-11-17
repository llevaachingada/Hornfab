"""Versioned Klangfilm-Lame Phase B core adapter (monotone H/V slope core).

`rows.type: klangfilm_lame_hv_core`, schema `klangfilm-lame-hv-core-canonical-v1`.

The implementation digest binds this adapter, the frozen core kernel, the frozen legacy parent kernel,
the frozen cap math and the shell mesher to every saved recipe. CPU geometry interface only: no acoustic
readiness claim, and no BEM has been run for this family.

Two geometry classes live behind one kernel, selected by a FIXED ``cd_core_blend``:

* ``0`` — the legacy v1 spherical-wave horn (bit-identical to ``klangfilm-lame-v1``);
* ``1`` — the monotone integrated-slope H/V core.

The classes are incompatible, so a study may not search ``cd_core_blend`` and may not search knobs of the
inactive class: that is enforced here (silent no-op genes are exactly what the 2026-11-16 handoff forbids).
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np
import scipy

from . import _klangfilm_lame_hv_core_v1 as kernel, _klangfilm_lame_v1 as parent
from . import _lame_cap_v1 as lame_cap
from . import lame_shell
from .registry import GeneratorError

KIND = kernel.KIND
SCHEMA = 'klangfilm-lame-hv-core-canonical-v1'
GRID_KEYS = frozenset({'n_phi', 'n_s', 'wall_thickness_mm'})
SPEC_KEYS = frozenset({'name', 'rows', 'n_phi', 'n_s', 'wall_thickness_mm', 'span', 'knobs',
                       'size_policy'})
SIZE_POLICIES = ('enforce', 'report_only')

_PARENT_KNOBS = frozenset(parent.SHAPE_KEYS - GRID_KEYS)
_CORE_KNOBS = frozenset(kernel.CORE_KEYS)
_INERT_AT_ZERO = _CORE_KNOBS - {'cd_core_blend'}
_INERT_AT_ONE = _PARENT_KNOBS


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
        raise GeneratorError('K core family requires an explicit driver')
    try:
        out = {k: float(driver[k]) for k in ('exit_radius_mm', 'exit_angle_deg')}
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError('driver radius and exit angle are required') from exc
    if not all(math.isfinite(v) for v in out.values()) or out['exit_radius_mm'] <= 0 or not 0 < out['exit_angle_deg'] < 45:
        raise GeneratorError('invalid driver radius or exit angle')
    return out


def _shape(spec, knobs, *, require_digest=False, brief=None):
    if not is_family_spec(spec) or set(spec) - SPEC_KEYS:
        raise GeneratorError('invalid canonical K-core specification')
    rows = spec['rows']
    if set(rows) - {'type', 'schema', 'implementation_sha256', 'driver'}:
        raise GeneratorError('unknown canonical K-core rows metadata')
    if spec.get('span', 'quarter') != 'quarter':
        raise GeneratorError('canonical K-core requires quarter symmetry')
    if spec.get('size_policy', 'enforce') not in SIZE_POLICIES:
        raise GeneratorError(f"size_policy must be one of {list(SIZE_POLICIES)}")
    if require_digest or 'implementation_sha256' in rows or 'schema' in rows or 'driver' in rows:
        if rows.get('schema') != SCHEMA or rows.get('implementation_sha256') != implementation_digest():
            raise GeneratorError('canonical K-core schema or implementation differs from saved recipe')
        saved = _driver(rows.get('driver'))
        if brief is not None and saved != _driver(brief.get('driver')):
            raise GeneratorError('canonical K-core driver differs from saved recipe')
    keys = kernel.SHAPE_KEYS - GRID_KEYS
    expected = {'g_' + k for k in keys}
    if not isinstance(knobs, dict) or set(knobs) != expected:
        raise GeneratorError(f'canonical K-core knob mismatch: expected {sorted(expected)}')
    try:
        shape = {k: knobs['g_' + k] for k in keys}
        shape.update({k: spec[k] for k in GRID_KEYS})
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in shape.values()):
            raise ValueError('shape values must be finite numbers')
        kernel.validate_shape(shape)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise GeneratorError(f'canonical K-core shape: {exc}') from exc
    return shape


def resolve_grid(block, brief):
    """Regenerate the saved inner surface and its sampled normal-offset shell."""
    driver = _driver((brief or {}).get('driver'))
    shape = _shape(block, block.get('knobs'), require_digest=True, brief=brief)
    if brief.get('mounting'):
        raise GeneratorError('canonical K-core explicit body cannot use a mounting enclosure')
    try:
        inner, meta = kernel.make_grid(shape, {'driver': driver})
        outer, metrics = lame_shell.offset_quarter_surface(inner, shape['wall_thickness_mm'])
        from . import grid
        grid.check_self_approach(inner, outer, shape['wall_thickness_mm'])
    except (ValueError, ArithmeticError) as exc:
        raise GeneratorError(f'canonical K-core geometry: {exc}') from exc
    both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    extents = (2 * np.max(abs(both[:, 0])), 2 * np.max(abs(both[:, 1])), np.ptp(both[:, 2]))
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
        raise GeneratorError('every canonical K-core knob needs an explicit matching bound')
    for key in expected:
        b, value = bounds[key], seed[key]
        if not all(math.isfinite(v) for v in (b.lo, b.hi, value)) or not b.lo <= value <= b.hi:
            raise GeneratorError(f'{key}: invalid bounds or seed')
        if not b.search and not b.lo == b.hi == value:
            raise GeneratorError(f'{key}: fixed bound must equal its seed')
        if b.log:
            raise GeneratorError('canonical K-core knobs require linear physical bounds')
        for endpoint in (b.lo, b.hi):
            _shape(spec, {**seed, key: endpoint}, brief=brief)
    blend = bounds['g_cd_core_blend']
    if blend.search:
        raise GeneratorError('cd_core_blend must be fixed: legacy and hv_core are separate geometry '
                             'classes and must not share one optimizer cohort')
    mode = 'legacy' if blend.lo == blend.hi == 0.0 else 'hv_core'
    dormant = _INERT_AT_ZERO if mode == 'legacy' else _INERT_AT_ONE
    for key in dormant:
        b, value = bounds['g_' + key], seed['g_' + key]
        if b.search or not b.lo == b.hi == value:
            raise GeneratorError(f'{key} is inert in {mode} mode and must be fixed at its seed')
    if spec.get('size_policy') == 'report_only' and any(b.search for b in bounds.values()):
        raise GeneratorError('size_policy report_only is a geometry/diagnostics lane; an enlarged-envelope '
                             'search requires a widened brief envelope')
