"""Original H/V mouth relief on the frozen section-based reference surface.

This is an ATH-inspired hypothesis, not Batik's OSSE or Tritonia construction.
See docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md.
"""
from __future__ import annotations

import math
import numpy as np
from tools.geometry import crowe_panel as base
from tools.geometry.rolled_rect import smoothstep

SCHEMA = 'section-pucker-study-v1'
REFERENCE = base.REFERENCE
PUCKER_KEYS = frozenset({'pucker_h_mm', 'pucker_v_mm', 'pucker_start_s',
                         'pucker_peak_s', 'pucker_end_s'})
SHAPE_KEYS = base.SHAPE_KEYS | PUCKER_KEYS


def validate_shape(shape):
    if set(shape) != SHAPE_KEYS:
        raise ValueError(f'section-pucker keys: missing={sorted(SHAPE_KEYS-set(shape))}, unknown={sorted(set(shape)-SHAPE_KEYS)}')
    base.validate_shape({k: shape[k] for k in base.SHAPE_KEYS})
    for key in PUCKER_KEYS:
        value = shape[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite')
    if not 0.15 <= shape['pucker_start_s'] < shape['pucker_peak_s'] < shape['pucker_end_s'] <= .96:
        raise ValueError('need .15 <= onset < peak < end <= .96')
    for key in ('pucker_h_mm', 'pucker_v_mm'):
        if not 0 <= shape[key] <= .1*shape['depth_mm']:
            raise ValueError('pucker must be nonnegative and at most 10 percent of depth')


def window(shape, stations):
    s = np.asarray(stations, dtype=float)
    start, peak, end = (shape[k] for k in ('pucker_start_s', 'pucker_peak_s', 'pucker_end_s'))
    return smoothstep((s-start)/(peak-start))*smoothstep((end-s)/(end-peak))


def _deform(points, shape, driver, stations):
    # Keep exact identity for the control, including floating-point point arrays.
    if shape['pucker_h_mm'] == shape['pucker_v_mm'] == 0:
        return points
    parent = {k: shape[k] for k in base.SHAPE_KEYS}
    ds, vertical, joint, _, _, _ = base._sweep(parent, driver)
    s = np.asarray(stations, dtype=float)
    h = np.interp(s, ds, joint[:, 0])
    v = np.interp(s, ds, vertical[:, 0])
    # Explicitly require a deformation-free driver matching region.
    active = window(shape, ds) > 0
    if np.any(vertical[active, 1] <= shape['throat_blend_mm']):
        raise ValueError('pucker window intersects the driver blend')
    psi = np.arctan2(points[..., 1]/v, points[..., 0]/h)
    amplitude = shape['pucker_h_mm']*np.cos(psi)**2 + shape['pucker_v_mm']*np.sin(psi)**2
    result = points.copy()
    result[..., 2] += amplitude*np.cos(4*psi)*window(shape, s)
    return result


def surface_at(shape, driver, stations, phis):
    validate_shape(shape)
    parent = {k: shape[k] for k in base.SHAPE_KEYS}
    return _deform(base.surface_at(parent, driver, stations, phis), shape, driver, stations)


def make_grid(shape, brief):
    validate_shape(shape)
    parent = {k: shape[k] for k in base.SHAPE_KEYS}
    points, meta = base.make_grid(parent, brief)
    points = _deform(points, shape, brief['driver'], meta['stations'])
    # The last two stations determine the existing outer-body endpoint normal.
    # Their whole neighbourhood must remain exactly undeformed.
    if np.any(window(shape, meta['stations'][-2:]) != 0):
        raise ValueError('pucker reaches the rear-body attachment normal')
    meta.update(construction_label=SCHEMA, shape=dict(shape), pucker_label='original H/V axial relief')
    return points, meta


def outer_points(inner, shape):
    return base.outer_points(inner, {k: shape[k] for k in base.SHAPE_KEYS})
