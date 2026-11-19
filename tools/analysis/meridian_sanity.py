"""Meridian sanity: S-curves, throat pinch and over-deep rollback in a horn's H and V sections (CPU).

For the H (phi = 0) and V (phi = 90 deg) meridians of a quarter grid it measures the wall direction
angle from the axis along arc length and flags:
* ``s_curve``: the wall's turning direction reverses (an inflection) by more than ``TOL_DEG`` net,
  i.e. the wall bends one way then the other (a shoulder or a pinch-then-flare);
* ``throat_pinch``: the wall angle drops more than ``TOL_DEG`` below its throat value before opening
  (a slot throat: the wall closes in, then has to flare hard later);
* ``deep_rollback``: total wall turn above ``MAX_TURN_DEG`` (past ~200 deg the lip curls back into the
  horn's own depth with little acoustic gain) or the lip returning below ``MIN_LIP_Z_FRAC`` of the depth.
A rolled lip that turns smoothly one way is NOT an S-curve, and a reversal of <= 10 deg in the last 10 %
of the wall is lip treatment (a beak), not an S-curve. Rollback is flagged above 230 deg of turn (JMLC
stop angles reach ~180-230) or when the lip returns into the first 35 % of the depth. Thresholds are review defaults, not physics.

    python tools/analysis/meridian_sanity.py CONFIG [CONFIG ...]   # seeds of generator/record configs
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TOL_DEG = 2.0
MAX_TURN_DEG = 230.0
LIP_ZONE = 0.10          # reversals in the last 10 % of the wall up to LIP_REVERSAL_DEG are lip treatment (beak, bead)
LIP_REVERSAL_DEG = 10.0
MIN_LIP_Z_FRAC = 0.35


def meridian(q, row):
    r = np.hypot(q[row, :, 0], q[row, :, 1])
    z = q[row, :, 2]
    t = np.degrees(np.unwrap(np.arctan2(np.diff(r), np.diff(z))))   # 0 = axial, 90 = radial, >90 = rolling back
    return r, z, t


def _reversals(t):
    """Net-angle runs: list of (net change, start fraction) of the monotone runs of the tangent angle."""
    runs, start, sign = [], 0, 0
    d = np.diff(t)
    for i, x in enumerate(d):
        s = 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)
        if s and sign and s != sign:
            runs.append((t[i] - t[start], start / len(t))); start = i
        if s:
            sign = s
    runs.append((t[-1] - t[start], start / len(t)))
    return [x for x in runs if abs(x[0]) > TOL_DEG]


def _profile_as_grid(prof):
    """A 2-row stand-in grid from FREEFORM [z, r, ...] meridian profiles (H row 0, V row -1)."""
    h, v = prof["profileH"], prof["profileV"]
    n = min(len(h), len(v))
    q = np.zeros((2, n, 3))
    q[0, :, 0], q[0, :, 2] = h[:n, 1], h[:n, 0]
    q[1, :, 1], q[1, :, 2] = v[:n, 1], v[:n, 0]
    return q


def check_grid(q) -> dict:
    if isinstance(q, dict):
        q = _profile_as_grid(q["profiles"])
    q = np.asarray(q, float)
    out = {"ok": True}
    for lab, row in (("h", 0), ("v", -1)):
        r, z, t = meridian(q, row)
        runs = _reversals(t)
        s_curve = len(runs) > 1 and any(x < 0 and not (u >= 1.0 - LIP_ZONE and -x <= LIP_REVERSAL_DEG)
                                        for x, u in runs)
        pinch = float(t[0] - t[: max(2, len(t) // 2)].min())
        turn = float(t.max() - t[0]) if t.max() > 0 else 0.0
        depth = float(z.max() - z.min())
        lip_frac = float((z[-1] - z.min()) / depth) if depth > 0 else 1.0
        flags = []
        if s_curve:
            flags.append("s_curve")
        if pinch > TOL_DEG:
            flags.append("throat_pinch")
        if float(t.max()) > MAX_TURN_DEG or (float(t.max()) > 90.0 and lip_frac < MIN_LIP_Z_FRAC):
            flags.append("deep_rollback")
        out[lab] = {"throat_deg": round(float(t[0]), 1), "max_wall_deg": round(float(t.max()), 1),
                    "pinch_deg": round(pinch, 1), "lip_z_frac": round(lip_frac, 2),
                    "runs_deg": [[round(x, 1), round(u, 2)] for x, u in runs], "flags": flags}
        out["ok"] = out["ok"] and not flags
    return out


def grid_for_config(path):
    """Seed geometry of a config. A warm_start is ignored (it needs runs/): this checks the config seed."""
    import tempfile

    import yaml
    from hornlab_search.config import load_config
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if (raw.get("search") or {}).pop("warm_start", None) is not None:
        bf = raw.get("brief_file")
        if bf and not Path(bf).is_absolute():
            raw["brief_file"] = str((Path(path).parent / bf).resolve())
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
            yaml.safe_dump(raw, fh)
            path = fh.name
    from hornlab_search.design.generators import grid as G
    from hornlab_search.design.space import DesignSpace
    cfg = load_config(path)
    sp = DesignSpace.from_config(cfg)
    seed = sp.design_from_knobs(dict(cfg.seed_params)) if hasattr(sp, "design_from_knobs") else sp.seed
    gb = (seed.params or {}).get("grid")
    if gb is None and "profileH" in (seed.params or {}):   # FREEFORM profile recipes (e.g. Crowe V2A)
        return {"profiles": {k: np.asarray(seed.params[k]["points"], float)
                             for k in ("profileH", "profileV")}}
    if gb is None:   # native mesher families (OSSE, R-OSSE, ...): needs hornlab_mesher (owner box)
        from hornlab_search.geometry.record import record_for_design
        return np.asarray(record_for_design(seed, cfg).inner, float)
    inner, _ = G.rows_grid_points(gb, gb.get("knobs", {}), cfg.brief)
    return np.asarray(inner, float)


def main(argv=None) -> int:
    paths = list(argv if argv is not None else sys.argv[1:])
    bad = 0
    for p in paths:
        try:
            res = check_grid(grid_for_config(p))
        except Exception as exc:  # noqa: BLE001
            print(f"{Path(p).name}: NOT CHECKED ({str(exc)[:100]})")
            continue
        bad += not res["ok"]
        f = lambda s: f"{s['flags'] or 'clean'} throat {s['throat_deg']} max {s['max_wall_deg']} pinch {s['pinch_deg']} lip_z {s['lip_z_frac']}"  # noqa: E731
        print(f"{Path(p).name}: {'OK ' if res['ok'] else 'BAD'} | H {f(res['h'])} | V {f(res['v'])}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
