"""Cross-family translation through shared descriptors (senior plan SD-1/SD-5, 2026-11-17).

"One description, plural generators": a design from family A is summarised by shared physical
descriptors from its canonical record (``sensitivity.shared_descriptors``); this module finds
the knob vector of family B whose record comes closest to those descriptors, by damped
Gauss-Newton on the descriptor Jacobian in B's unit coordinates (box-clipped, every step checked
on a REAL record, backtracking on refusal or envelope breach). The result is a SEED for B, not a
claim of acoustic equivalence: equal mouth size and wall angles do not make two constructions
sound alike, and the residual says how close the geometry got.

Typical uses: seed a new or protected lane from another lane's best design; compare families at
matched size; give an owner-stated geometry ("600 x 450 mouth, 380 deep") to any family.
"""
from __future__ import annotations

import math

import numpy as np

from .sensitivity import (DESCRIPTOR_KEYS, _envelope, inside, jacobian, record_at,
                          searched_keys, seed_unit, shared_descriptors)

#: Default descriptor scales: a residual of 1.0 in each = 1 mm, 1 deg, 0.02 aspect, 2000 mm^2.
DEFAULT_SCALES = {"mouth_width_mm": 1.0, "mouth_height_mm": 1.0, "depth_mm": 1.0,
                  "h_wall_angle_mouth_deg": 1.0, "v_wall_angle_mouth_deg": 1.0,
                  "diag_wall_angle_mouth_deg": 1.0, "mouth_aspect": 0.02,
                  "mouth_area_mm2": 2000.0, "h_halfwidth_mid_mm": 1.0, "v_halfwidth_mid_mm": 1.0}
DEFAULT_TARGET_KEYS = ("mouth_width_mm", "mouth_height_mm", "depth_mm",
                       "h_wall_angle_mouth_deg", "v_wall_angle_mouth_deg",
                       "h_halfwidth_mid_mm", "v_halfwidth_mid_mm")


def _resid(desc: dict, target: dict, keys, scales) -> np.ndarray:
    return np.array([(desc[k] - target[k]) / scales[k] for k in keys])


def match_descriptors(space, cfg, target: dict, *, keys=None, scales=None, x_init=None,
                      iters: int = 10, h: float = 0.02, damping: float = 1e-2,
                      require_inside: bool = True) -> dict:
    """Find ``x`` in ``space``'s unit box whose record's shared descriptors best match ``target``.

    Returns ``{x, knobs, descriptors, residual_rms, history, ok}``; ``ok`` is False when the start
    point itself is not a legal (inside) record. ``knobs`` are in the space's own units."""
    keys = [k for k in (keys or DEFAULT_TARGET_KEYS) if k in target]
    if not keys:
        raise ValueError(f"target names none of {list(DEFAULT_TARGET_KEYS)}")
    sc = {**DEFAULT_SCALES, **(scales or {})}
    env = _envelope(cfg) if require_inside else {}
    x = np.clip(np.asarray(seed_unit(space) if x_init is None else x_init, float), 0.0, 1.0)
    rec, why = record_at(space, cfg, x)
    if rec is None or (env and not inside(rec, env)):
        return {"ok": False, "reason": why or "start point outside the envelope", "x": x.tolist()}
    desc = shared_descriptors(rec)
    r = _resid(desc, target, keys, sc)
    hist = [float(np.sqrt(np.mean(r ** 2)))]
    lam = damping
    for _ in range(iters):
        J = jacobian(space, cfg, x, h=h)
        A = np.array([J.desc[DESCRIPTOR_KEYS.index(k)] / sc[k] for k in keys])   # (m, k)
        if not np.any(A):
            break
        step = None
        for _bt in range(8):
            H = A.T @ A + lam * np.eye(A.shape[1])
            dx = -np.linalg.solve(H, A.T @ r)
            xn = np.clip(x + dx, 0.0, 1.0)
            rn_rec, _ = record_at(space, cfg, xn)
            if rn_rec is not None and (not env or inside(rn_rec, env)):
                dn = shared_descriptors(rn_rec)
                rn = _resid(dn, target, keys, sc)
                if np.sqrt(np.mean(rn ** 2)) < hist[-1]:
                    step = (xn, rn_rec, dn, rn)
                    lam = max(lam / 3.0, 1e-6)
                    break
            lam *= 4.0
        if step is None:
            break
        x, rec, desc, r = step
        hist.append(float(np.sqrt(np.mean(r ** 2))))
        if hist[-1] < 0.05 or (len(hist) > 2 and hist[-2] - hist[-1] < 1e-3 * hist[-2]):
            break
    design = space.denormalize(x)
    knobs = {}
    for i, k in enumerate(searched_keys(space)):
        b = space.bounds[k]
        knobs[k] = float(b.lo + x[i] * (b.hi - b.lo)) if not getattr(b, "log", False) else \
            float(math.exp(math.log(b.lo) + x[i] * (math.log(b.hi) - math.log(b.lo))))
    return {"ok": True, "x": x.tolist(), "knobs": knobs, "design_hash": design.hash(),
            "descriptors": {k: float(desc[k]) for k in DESCRIPTOR_KEYS},
            "target": {k: float(target[k]) for k in keys},
            "residual_by_key": {k: float(desc[k] - target[k]) for k in keys},
            "residual_rms_scaled": hist[-1], "history": hist}


def descriptors_of_design(design, cfg) -> dict:
    from .record import record_for_design
    return shared_descriptors(record_for_design(design, cfg))


__all__ = ["match_descriptors", "descriptors_of_design", "DEFAULT_SCALES", "DEFAULT_TARGET_KEYS"]
