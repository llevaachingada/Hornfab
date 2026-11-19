"""Offline geometry verification for the 2026-11-19 owner-directed construction fixes.

READ-ONLY. No mesh, no GPU. Two questions:
  1. Klangfilm Phase B core at the c200 mouth seed: are the H/V wall angles monotone and the radii
     strictly increasing (i.e. no pinch and no S-curve by construction)? What mouth does it give?
  2. Rolled whole-shape: how many inflections does the H wall have at the old fixed depth ratio 0.68
     vs the new seed 1.0, at terminal 225 vs 270? How far does the lip return toward the throat?
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hornlab_search.design.generators import _klangfilm_lame_hv_core_v1 as core  # noqa: E402
from hornlab_search.design.generators import _rolled_rect_v1 as rect  # noqa: E402

CFG_DIR = ROOT / "examples" / "typologies" / "scout40_2026-11-19"


def _shape_from_config(name: str) -> dict:
    cfg = yaml.safe_load((CFG_DIR / name).read_text(encoding="utf-8"))
    sp = cfg["seed_params"]
    return {k[2:]: float(v) for k, v in sp.items() if k.startswith("g_")}, cfg


def _rolled_kernel_shape(cfg: dict) -> dict:
    """Map the rolled-family g_* knobs onto the frozen rect kernel's SHAPE_KEYS.

    The family adapter forces the legacy pucker slots neutral (pucker 0, start = rect_turn_deg);
    relief keys (inward/axial) are applied by the adapter after the kernel, so this check reads the
    parent wall. Inward relief is 0 in both arms; axial relief is +/-5 mm (small, late).
    """
    sp = cfg["seed_params"]
    grid = cfg["generator"]
    keys = set(rect.SHAPE_KEYS) - {"pucker_h_mm", "pucker_v_mm", "pucker_start_deg"}
    shape = {k: float(sp["g_" + k]) if "g_" + k in sp else float(grid[k]) for k in keys}
    shape.update(pucker_h_mm=0.0, pucker_v_mm=0.0,
                 pucker_start_deg=float(sp["g_rect_turn_deg"]))
    return shape


def _brief_driver(cfg: dict) -> dict:
    brief_path = (CFG_DIR / cfg["brief_file"]).resolve()
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    drv = brief.get("driver") or {}
    return {
        "exit_radius_mm": float(drv.get("exit_radius_mm", 18.0)),
        "exit_angle_deg": float(drv.get("exit_angle_deg", 2.0)),
    }


def _inflections(x: np.ndarray, z: np.ndarray) -> int:
    """Sign changes of the tangent angle along a 2D polyline (analytic, dense)."""
    dx, dz = np.diff(x), np.diff(z)
    ang = np.unwrap(np.arctan2(dz, dx))
    d = np.diff(ang)
    return int(np.count_nonzero(np.sign(d[1:]) != np.sign(d[:-1]))), float(np.degrees(ang[-1] - ang[0]))


def klangfilm_core() -> None:
    shape, _cfg = _shape_from_config("scout40__klangfilm_hvcore_c200mouth.yaml")
    tab = core.core_table(shape, 18.0)
    th, tv = tab["theta_h"], tab["theta_v"]
    a, b = tab["a"], tab["b"]

    def signs(v):
        d = np.diff(v)
        return int(np.count_nonzero(np.sign(d[1:]) != np.sign(d[:-1])))

    print("== Klangfilm Phase B core (klangfilm_lame_hv_core), seed = c200 mouth ==")
    print(f"theta_h range: {np.degrees(th[0]):.3f} -> {np.degrees(th[-1]):.3f} deg; angle inflections: {signs(th)}")
    print(f"theta_v range: {np.degrees(tv[0]):.3f} -> {np.degrees(tv[-1]):.3f} deg; angle inflections: {signs(tv)}")
    print(f"d(a)/dz min: {np.diff(a).min():.6f} mm  d(b)/dz min: {np.diff(b).min():.6f} mm  (must be > 0)")
    print(f"inner mouth: {2*a[-1]:.3f} x {2*b[-1]:.3f} mm; axial length {tab['z'][-1]:.3f} mm")
    print()


def rolled(name: str, ratios=(0.68, 1.0), terminals=None) -> None:
    _seed, cfg = _shape_from_config(name)
    shape = _rolled_kernel_shape(cfg)
    driver = _brief_driver(cfg)
    terminal = shape["terminal_deg"]
    print(f"== Rolled whole-shape: {name} (seed terminal {terminal:.0f} deg) ==")
    print(f"driver: r {driver['exit_radius_mm']} mm, half-angle {driver['exit_angle_deg']} deg")
    for ratio in ratios:
        sh = dict(shape)
        sh["depth_h_ratio"] = ratio
        for terminal_deg in ([terminal] if terminals is None else terminals):
            sh["terminal_deg"] = float(terminal_deg)
            t = np.linspace(0, math.radians(terminal_deg), 4097)
            p = rect.surface_at(sh, driver, t, [0.0])[0]   # phi=0 -> H meridian (x, z)
            q = rect.surface_at(sh, driver, t, [math.pi / 2])[0]  # phi=90 -> V meridian (y, z)
            n_h, turn_h = _inflections(p[:, 0], p[:, 2])
            n_v, turn_v = _inflections(q[:, 1], q[:, 2])
            zmax, zend = float(p[:, 2].max()), float(p[-1, 2])
            ret = (zmax - zend) / zmax if zmax else float("nan")
            print(f"  depth_h_ratio {ratio:.2f} terminal {terminal_deg:3.0f}: "
                  f"H inflections {n_h} (total turn {turn_h:.1f} deg), V inflections {n_v}; "
                  f"max depth {zmax:.1f} mm, lip z {zend:.1f} mm, return {100*ret:.1f}% of depth")
    print()


if __name__ == "__main__":
    klangfilm_core()
    rolled("scout40__rf_rect_axial_cap225.yaml", ratios=(0.68, 1.0))
    rolled("scout40__rf_rect_axial_control270.yaml", ratios=(0.68, 1.0))
