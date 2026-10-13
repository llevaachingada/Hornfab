"""Room geometry -> coverage target, and the physical-feasibility check.

Pure trigonometry and the Keele relation. No solver, no mesher.
"""
from __future__ import annotations

import math

from ..constants import KEELE_K
from .spec import Target

# Band defaults used only when a caller builds a Target from a room and does not say
# which band to hold. They mirror the target block of examples/osse_baseline.yaml.
DEFAULT_BAND_LO_HZ = 700.0
DEFAULT_BAND_HI_HZ = 13000.0


def coverage_from_room(listener_width_m, depth_near_m, depth_far_m,
                       height_m, ear_height_m=1.2, source_height_m=2.0,
                       splay_deg=0.0, *,
                       band_lo_hz: float = DEFAULT_BAND_LO_HZ,
                       band_hi_hz: float = DEFAULT_BAND_HI_HZ) -> Target:
    """Coverage angles that put the listening area inside the pattern.

    Geometry (the horn sits on the room centre line, `source_height_m` above the floor;
    depths are horizontal distances from the horn mouth to the near and far listener
    rows; listeners' ears are at `ear_height_m`):

      Horizontal: the widest angle is at the NEAR row. Each half-angle is
          atan( (listener_width_m / 2) / depth_near_m )
      and `splay_deg` is the angle the horn axis is turned off the room centre line;
      a symmetric pattern must then cover the room edge plus the splay on the far side:
          coverage_h = 2 * ( atan(w/2 / near) + |splay| )

      Vertical: the horn is assumed tilted to aim at the middle of the elevation range
      the ears span, so the total included angle is just that range:
          coverage_v = | atan((ear - src)/near) - atan((ear - src)/far) |

    `height_m` is the ceiling height. It is only used to reject an impossible source or
    ear height; the ceiling is not a coverage target. The vertical angle is the
    geometric minimum for one ear height; nothing here pads it for seated vs standing
    audiences, the user widens the target if wanted.

    Raises ValueError for non-positive widths or depths, far < near, a source or
    ear above the ceiling, or a degenerate (zero) vertical range.
    """
    w = float(listener_width_m)
    near = float(depth_near_m)
    far = float(depth_far_m)
    if not (w > 0 and near > 0 and far >= near):
        raise ValueError("coverage_from_room: need width > 0, 0 < depth_near <= depth_far")
    if not (float(height_m) > 0 and 0 <= float(source_height_m) <= float(height_m)
            and 0 <= float(ear_height_m) <= float(height_m)):
        raise ValueError("coverage_from_room: source and ear heights must lie within [0, height_m]")

    half_h = math.atan((w / 2.0) / near) + math.radians(abs(float(splay_deg)))
    drop = float(ear_height_m) - float(source_height_m)
    v = abs(math.atan(drop / near) - math.atan(drop / far))
    h_deg = 2.0 * math.degrees(half_h)
    v_deg = math.degrees(v)
    if not (0.0 < v_deg and 0.0 < h_deg < 180.0):
        raise ValueError(
            f"coverage_from_room: degenerate coverage (H {h_deg:.2f}, V {v_deg:.2f} deg); "
            "check depths and heights")
    return Target(coverage_h_deg=h_deg, coverage_v_deg=v_deg,
                  band_lo_hz=float(band_lo_hz), band_hi_hz=float(band_hi_hz),
                  di_target_db=None)


def required_mouth_m(coverage_total_deg: float, f_lo_hz: float) -> float:
    """From KEELE_K: d = KEELE_K / (f_lo * coverage_deg).

    The mouth dimension that axis needs to hold pattern down to f_lo."""
    if not (coverage_total_deg > 0 and f_lo_hz > 0):
        raise ValueError("required_mouth_m: coverage and frequency must be positive")
    return KEELE_K / (float(f_lo_hz) * float(coverage_total_deg))


def feasibility_report(target: Target, mouth_limit_m: float | None = None) -> dict:
    """{'mouth_h_m', 'mouth_v_m', 'note'}. Says in plain words whether the target is
    physically possible at a sane size.

    mouth_h_m / mouth_v_m are the mouth width / height needed to hold the target
    coverage down to target.band_lo_hz. If `mouth_limit_m` is given, the note also says
    whether each fits within it. A design check, never a constraint on the search.
    """
    mh = required_mouth_m(target.coverage_h_deg, target.band_lo_hz)
    mv = required_mouth_m(target.coverage_v_deg, target.band_lo_hz)
    note = (
        f"Holding {target.coverage_h_deg:.0f} deg horizontally and "
        f"{target.coverage_v_deg:.0f} deg vertically down to {target.band_lo_hz:.0f} Hz "
        f"needs about {mh:.2f} m of mouth width ({mh / 0.0254:.0f} in) and "
        f"{mv:.2f} m of mouth height ({mv / 0.0254:.0f} in). "
    )
    narrow = "vertical" if mv > mh else "horizontal"
    note += (f"The narrower pattern ({narrow}) needs the larger mouth. "
             "Pattern control is lost below these frequencies for a smaller mouth.")
    if mouth_limit_m is not None:
        fits_h = mh <= mouth_limit_m
        fits_v = mv <= mouth_limit_m
        if fits_h and fits_v:
            note += f" Both fit within the {mouth_limit_m:.2f} m limit."
        else:
            bad = [n for n, ok in (("width", fits_h), ("height", fits_v)) if not ok]
            note += (f" The mouth {' and '.join(bad)} exceed(s) the {mouth_limit_m:.2f} m limit: "
                     "this target cannot be held to the band edge at that size.")
    return {"mouth_h_m": mh, "mouth_v_m": mv, "note": note}
