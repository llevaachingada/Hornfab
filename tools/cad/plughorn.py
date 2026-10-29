"""Cone mid horn with a central axe-head plug (Funktion-One Evo SH style) -> labelled STEP.

LABELED HYPOTHESIS-SHAPE EXPERIMENT under a neutral name. The topology and the default numbers come from
Funktion-One's own 3D models of the Evo 7SH (narrow, 40 x 20) and Evo 2SH (wide, 50) skeletal horns,
supplied by the owner on 2026-10-28 as DWG, converted with the ODA File Converter to DXF R2000 and read
with ``tools/cad/sat_dump.py`` (vertices in ``reference/funktion-one/*_topology.json``, not committed).
Images (website drawings, photos) were used only as a check. Defaults = Evo 7SH; the Evo 2SH numbers are
in ``examples/typologies/cone_plughorn_2026-10-28/``. Like ``multicell.py`` this is a *tool*: every number
is a documented default and a CLI argument.

The model (all lengths mm; ``d`` = depth behind the front face; mirror-symmetric in x and y)
------------------------------------------------------------------------------------------
* **Throat** at ``d = length``: an octagon - side edge ``x = throat_side_x`` for ``|y| <= throat_side_half``,
  top edge ``y = throat_top_y`` for ``|x| <= throat_top_half``, long diagonal edges between them. This is
  where the cone fires in; the cone sits ``front_gap`` behind it in a round chamber of radius ``cone_r``
  (the ring between the octagon and the cone is the compression face).
* **Walls** (as in the CAD): ONE flat top plane, ONE flat side plane per side, and a twisted (ruled) corner
  panel per corner, running straight from the throat octagon to where the roll-out starts:
  side at ``x = mouth_side_x`` (``|y| <= mouth_side_half``, depth ``mouth_side_d``), top at
  ``y = mouth_top_y`` (``|x| <= mouth_top_half``, depth ``mouth_top_d``).
* **Roll-out**: a quarter-ellipse roundover from there to the front face opening (``front_side_x``,
  ``front_top_y`` at ``d = 0``), built from ``roll_steps`` bands (flat on the sides, ruled at the corners).
* **Axe head** (convex polyhedron, planar faces - planar in the CAD to 0.01 mm): nose on the axis at
  ``plug_nose_d``; horizontal blade from the nose to the side tips (``plug_tip_x`` at ``plug_tip_d``); vertical
  ridges to ``plug_top_y`` at ``plug_top_d``; corners (``plug_corner_x``, ``plug_corner_y``) at the depth
  that keeps each front face planar (derived); base octagon (``plug_base_x``/``plug_base_side_y``, ``plug_base_top_x``/``plug_base_y``)
  just behind the throat plane, carried on a post (radius ``post_r``) from the cone centre (US6557664: the
  member is mounted inside the voice-coil diameter), so horn + plug are ONE solid.
* **Outside** (simplified, owner 2026-10-28): front plate ``plate_w x plate_h x plate_t``, a convex shell from
  the plate's back (``shell_w x shell_h``) to the driver ring, and the moulded driver bowl (``bowl_*``), whose
  gross air volume is reported for the lumped driver model.
* ``scale`` multiplies every horn / axe-head / outside length (not the driver).

Coordinates for the solid: +z toward the mouth, throat plane ``z = 0``, front face ``z = length``.
Driver: the cone face (between the post and the cone rim) is the single ``driver`` face (BEM tag 2).
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent


def _multicell():
    """The sibling multicell tool: the labelled-STEP writer + round trip are reused, not copied."""
    name = "hornlab_search_cad_multicell"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HERE / "multicell.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass(frozen=True)
class PlughornParams:
    # driver (10-inch mid cone) behind the throat
    cone_r_mm: float = 105.0           # 10-inch effective radius (Sd ~ 346 cm^2)
    cone_depth_mm: float = 45.0
    post_r_mm: float = 22.0
    front_gap_mm: float = 8.0          # throat plane -> cone rim (the compression chamber depth)
    # horn (Evo 7SH CAD)
    length_mm: float = 400.0           # front face -> throat plane
    throat_side_x_mm: float = 90.0
    throat_side_half_mm: float = 22.5
    throat_top_y_mm: float = 90.0
    throat_top_half_mm: float = 15.6
    mouth_side_x_mm: float = 252.2
    mouth_side_half_mm: float = 151.4
    mouth_side_d_mm: float = 18.3
    mouth_top_y_mm: float = 162.3
    mouth_top_half_mm: float = 235.4
    mouth_top_d_mm: float = 24.3
    front_side_x_mm: float = 279.8
    front_top_y_mm: float = 191.8
    roll_steps: int = 4
    # outside (simplified) + driver bowl
    plate_w_mm: float = 606.0
    plate_h_mm: float = 422.0
    plate_t_mm: float = 20.0
    shell_w_mm: float = 584.0
    shell_h_mm: float = 404.0
    bowl_r1_mm: float = 130.0          # at the throat plane
    bowl_r2_mm: float = 114.7
    bowl_len_mm: float = 145.2         # r1 -> r2
    bowl_back_r_mm: float = 65.0
    bowl_back_d_mm: float = 190.0      # total bowl depth behind the throat plane
    wall_mm: float = 6.0               # bowl wall (for the rear-chamber volume only)
    # axe head (Evo 7SH CAD)
    plug_nose_d_mm: float = 12.7
    plug_tip_x_mm: float = 203.2
    plug_tip_d_mm: float = 66.8
    plug_top_y_mm: float = 67.0
    plug_top_d_mm: float = 231.4
    plug_corner_x_mm: float = 87.1
    plug_corner_y_mm: float = 68.3
    plug_base_x_mm: float = 75.0
    plug_base_side_y_mm: float = 0.0   # 0 = hexagon base (Evo 7SH)
    plug_base_top_x_mm: float = 28.6
    plug_base_y_mm: float = 75.0
    plug_base_back_mm: float = 2.0     # the base sits this far behind the throat plane (in the chamber)
    plug_gap_mm: float = 2.0           # min clearance plug <-> walls / cone (the CAD has 2.4 mm at the throat diagonals)
    scale: float = 1.0
    # ---- MORPH knobs (horn-theory levers; 0 = off, the raw dimensions above are used as they are). When on,
    # each one DERIVES raw dimensions, in this order, so the shape stays consistent while a search moves it.
    # Values that reproduce the Evo 7SH CAD are in the docstring of ``resolve_morph``.
    m_compression_ratio: float = 0.0   # Sd / (throat octagon - axe-head base) area: sizes the throat for the cone
    m_plug_base_frac: float = 0.0      # axe-head base x / throat x (base keeps its shape); sets the throat ring width
    m_wall_angle_h_deg: float = 0.0    # side-wall half-angle (throat edge -> wall end): horizontal pattern
    m_wall_angle_v_deg: float = 0.0    # top-wall half-angle: vertical pattern
    m_mouth_corner_frac: float = 0.0   # mouth corner chamfer as a fraction of the wall-end size
    m_roll_h_mm: float = 0.0           # side roll-out radial size (wall end -> front opening)
    m_roll_v_mm: float = 0.0           # top/bottom roll-out radial size
    m_plug_width_frac: float = 0.0     # axe-head tips / front-opening half-width
    m_plug_nose_frac: float = 0.0      # nose depth / length
    m_plug_tip_frac: float = 0.0       # tip depth / length (blade sweep = tip - nose)
    m_plug_ridge_frac: float = 0.0     # ridge-end depth / length (vertical wedge length)
    m_plug_height_frac: float = 0.0    # axe-head half-height / throat half-height
    m_plug_flat_frac: float = 0.0      # flat top half-length / tip half-width
    m_plate_margin_mm: float = 0.0     # front plate border around the opening (shell follows)
    m_bowl_auto: float = 0.0           # 1 = size the driver bowl from the cone (rear-chamber proportions of the CAD)

    def s(self, name: str) -> float:
        return getattr(self, name) * self.scale

    def morph_active(self) -> bool:
        return any(getattr(self, f.name) for f in fields(self) if f.name.startswith("m_"))

    def resolve_morph(self) -> "PlughornParams":
        """Apply the m_* knobs: return a copy whose RAW dimensions are derived from them (m_* kept).

        Physics of each lever (cone mid horn with an axe-head phase plug):
        * m_compression_ratio + m_plug_base_frac -> throat size. The ring between the throat octagon and the
          axe-head base is the horn's real throat (Sd / ring = compression ratio). Higher CR = more loading and
          efficiency in the lower mids, a lower front-chamber cut-off and more air-load distortion. The
          octagon/base SHAPES stay those of the current raw values; only their size moves.
        * m_wall_angle_h/v -> wall-end positions: straight (conical) walls from the throat edges; the -6 dB
          coverage of a CD wall section is close to twice the wall angle (Evo 7SH 23 / 10.9 deg for 40 x 20,
          Evo 2SH 31.6 / 13.6 deg for 50 x 25). With ``length`` they set the mouth size, i.e. the lowest
          frequency the pattern is held (K-law, see ``derived``).
        * m_mouth_corner_frac -> the twisted corner panels' size (both CADs: ~0.07).
        * m_roll_h/v -> the roll-out (mouth termination): larger = less edge diffraction, wider opening.
        * m_plug_* -> the axe head relative to the horn it sits in (both CADs: width 0.72 of the opening,
          ridge end at ~0.6 of the length): the blade splits the throat into two wide slots (wide H, controlled V).
        * m_plate_margin / m_bowl_auto -> the outside follows the horn / the cone.
        Evo 7SH-equivalent settings: CR 5.0, base 0.833, walls 23.0 / 10.9, corner 0.067, roll 27.6 / 29.5,
        plug width 0.726, nose 0.032, tip 0.167, ridge 0.579, height 0.744, flat 0.429, margin 23.2.
        """
        if not self.morph_active():
            return self
        sc = self.scale
        g = {f.name: getattr(self, f.name) * (sc if f.name.endswith("_mm") and not f.name.startswith(("cone_",
             "post_", "front_gap", "plug_gap", "plug_base_back", "wall_mm")) else 1.0) for f in fields(self)}
        L = g["length_mm"]
        # --- throat: scale the octagon (and the base with it) to hit the compression ratio
        tsx, tsh, tty, tth = g["throat_side_x_mm"], g["throat_side_half_mm"], g["throat_top_y_mm"], g["throat_top_half_mm"]
        bx, bsy, btx, by = g["plug_base_x_mm"], g["plug_base_side_y_mm"], g["plug_base_top_x_mm"], g["plug_base_y_mm"]
        if self.m_plug_base_frac:              # base x = frac * throat x; the base keeps its own shape
            k_b = self.m_plug_base_frac * tsx / bx
            bx, bsy, btx, by = bx * k_b, bsy * k_b, btx * k_b, by * k_b
        if self.m_compression_ratio:
            sd = math.pi * (self.cone_r_mm ** 2 - self.post_r_mm ** 2)
            octa = _poly_area(np.array([(x, y) for x, y, _ in self._octagon((tsx, tsh, 0), (tth, tty, 0))]))
            base = _poly_area(_hull2d([(sx * bx, sy * bsy) for sx in (1, -1) for sy in (1, -1)]
                                      + [(sx * btx, sy * by) for sx in (1, -1) for sy in (1, -1)]))
            k = math.sqrt(sd / self.m_compression_ratio / max(octa - base, 1e-9))
            tsx, tsh, tty, tth, bx, bsy, btx, by = (v * k for v in (tsx, tsh, tty, tth, bx, bsy, btx, by))
        # --- walls, mouth corner, roll-out
        msd, mtd = g["mouth_side_d_mm"], g["mouth_top_d_mm"]
        msx, mty = g["mouth_side_x_mm"], g["mouth_top_y_mm"]
        if self.m_wall_angle_h_deg:
            msx = tsx + math.tan(math.radians(self.m_wall_angle_h_deg)) * (L - msd)
        if self.m_wall_angle_v_deg:
            mty = tty + math.tan(math.radians(self.m_wall_angle_v_deg)) * (L - mtd)
        c = self.m_mouth_corner_frac or (1.0 - g["mouth_side_half_mm"] / g["mouth_top_y_mm"])
        msh, mth = (1.0 - c) * mty, (1.0 - c) * msx
        rh = self.m_roll_h_mm * sc if self.m_roll_h_mm else g["front_side_x_mm"] - g["mouth_side_x_mm"]
        rv = self.m_roll_v_mm * sc if self.m_roll_v_mm else g["front_top_y_mm"] - g["mouth_top_y_mm"]
        msd = msd * (rh / max(g["front_side_x_mm"] - g["mouth_side_x_mm"], 1e-9))
        mtd = mtd * (rv / max(g["front_top_y_mm"] - g["mouth_top_y_mm"], 1e-9))
        if self.m_wall_angle_h_deg:                       # depth of the wall end moved with the roll-out
            msx = tsx + math.tan(math.radians(self.m_wall_angle_h_deg)) * (L - msd)
            mth = (1.0 - c) * msx
        if self.m_wall_angle_v_deg:
            mty = tty + math.tan(math.radians(self.m_wall_angle_v_deg)) * (L - mtd)
            msh = (1.0 - c) * mty
        fsx, fty = msx + rh, mty + rv
        # --- axe head relative to the horn
        tip_x = self.m_plug_width_frac * fsx if self.m_plug_width_frac else g["plug_tip_x_mm"]
        nose_d = self.m_plug_nose_frac * L if self.m_plug_nose_frac else g["plug_nose_d_mm"]
        tip_d = self.m_plug_tip_frac * L if self.m_plug_tip_frac else g["plug_tip_d_mm"]
        top_d = self.m_plug_ridge_frac * L if self.m_plug_ridge_frac else g["plug_top_d_mm"]
        top_y = self.m_plug_height_frac * tty if self.m_plug_height_frac else g["plug_top_y_mm"]
        cy = top_y * (g["plug_corner_y_mm"] / g["plug_top_y_mm"])
        cx = self.m_plug_flat_frac * tip_x if self.m_plug_flat_frac else g["plug_corner_x_mm"]
        # --- outside
        pw, ph, sw, sh = g["plate_w_mm"], g["plate_h_mm"], g["shell_w_mm"], g["shell_h_mm"]
        if self.m_plate_margin_mm:
            m = self.m_plate_margin_mm * sc
            pw, ph, sw, sh = 2 * fsx + 2 * m, 2 * fty + 2 * m, 2 * fsx + m, 2 * fty + m
        bowl = {}
        if self.m_bowl_auto:
            r1 = 1.24 * self.cone_r_mm
            bd_ = 1.7 * self.cone_r_mm
            bowl = {"bowl_r1_mm": r1, "bowl_r2_mm": 0.88 * r1, "bowl_len_mm": 0.76 * bd_,
                    "bowl_back_r_mm": 0.5 * r1, "bowl_back_d_mm": bd_}
            bowl = {k: v / sc for k, v in bowl.items()}
        raw = {"throat_side_x_mm": tsx, "throat_side_half_mm": tsh, "throat_top_y_mm": tty, "throat_top_half_mm": tth,
               "plug_base_x_mm": bx, "plug_base_side_y_mm": bsy, "plug_base_top_x_mm": btx, "plug_base_y_mm": by,
               "mouth_side_x_mm": msx, "mouth_side_half_mm": msh, "mouth_side_d_mm": msd, "mouth_top_y_mm": mty,
               "mouth_top_half_mm": mth, "mouth_top_d_mm": mtd, "front_side_x_mm": fsx, "front_top_y_mm": fty,
               "plug_tip_x_mm": tip_x, "plug_nose_d_mm": nose_d, "plug_tip_d_mm": tip_d, "plug_top_d_mm": top_d,
               "plug_top_y_mm": top_y, "plug_corner_y_mm": cy, "plug_corner_x_mm": cx,
               "plate_w_mm": pw, "plate_h_mm": ph, "shell_w_mm": sw, "shell_h_mm": sh}
        raw = {k: v / sc for k, v in raw.items()}
        return replace(self, **raw, **bowl)

    @property
    def L(self) -> float:
        return self.s("length_mm")

    # ------------------------------------------------------------------ vertices
    def horn_points(self) -> dict[str, tuple[float, float, float]]:
        """First-quadrant key vertices (z = L - d)."""
        L = self.L
        return {
            "R": (self.s("throat_side_x_mm"), self.s("throat_side_half_mm"), 0.0),
            "Q": (self.s("throat_top_half_mm"), self.s("throat_top_y_mm"), 0.0),
            "Ms": (self.s("mouth_side_x_mm"), self.s("mouth_side_half_mm"), L - self.s("mouth_side_d_mm")),
            "Mt": (self.s("mouth_top_half_mm"), self.s("mouth_top_y_mm"), L - self.s("mouth_top_d_mm")),
        }

    def roll_points(self):
        """Roll-out stations: (side vertex, top vertex) per quarter-ellipse step, wall end -> front face."""
        L, n = self.L, max(1, int(self.roll_steps))
        msx, msh, msd = self.s("mouth_side_x_mm"), self.s("mouth_side_half_mm"), self.s("mouth_side_d_mm")
        mty, mth, mtd = self.s("mouth_top_y_mm"), self.s("mouth_top_half_mm"), self.s("mouth_top_d_mm")
        fsx, fty = self.s("front_side_x_mm"), self.s("front_top_y_mm")
        out = []
        for k in range(n + 1):
            ph = 0.5 * math.pi * k / n
            side = (fsx - (fsx - msx) * math.cos(ph), msh, L - msd + msd * math.sin(ph))
            top = (mth, fty - (fty - mty) * math.cos(ph), L - mtd + mtd * math.sin(ph))
            out.append((side, top))
        return out

    def horn_faces(self) -> list[tuple[str, list[tuple[float, float, float]]]]:
        """Wall faces: ("plane", polygon) or ("ruled", [a, b, c, d] ruled between a-b and d-c)."""
        hp = self.horn_points()

        def m(p, sx, sy):
            return (sx * p[0], sy * p[1], p[2])
        R, Q, Ms, Mt = hp["R"], hp["Q"], hp["Ms"], hp["Mt"]
        roll = self.roll_points()
        faces = []
        for sy in (1, -1):
            faces.append(("plane", [m(Q, 1, sy), m(Mt, 1, sy), m(Mt, -1, sy), m(Q, -1, sy)]))
        for sx in (1, -1):
            faces.append(("plane", [m(R, sx, -1), m(Ms, sx, -1), m(Ms, sx, 1), m(R, sx, 1)]))
        for sx in (1, -1):
            for sy in (1, -1):
                faces.append(("ruled", [m(R, sx, sy), m(Ms, sx, sy), m(Mt, sx, sy), m(Q, sx, sy)]))
        for (s0, t0), (s1, t1) in zip(roll, roll[1:]):
            for sy in (1, -1):
                faces.append(("plane", [m(t0, 1, sy), m(t1, 1, sy), m(t1, -1, sy), m(t0, -1, sy)]))
            for sx in (1, -1):
                faces.append(("plane", [m(s0, sx, -1), m(s1, sx, -1), m(s1, sx, 1), m(s0, sx, 1)]))
            for sx in (1, -1):
                for sy in (1, -1):
                    faces.append(("ruled", [m(s0, sx, sy), m(s1, sx, sy), m(t1, sx, sy), m(t0, sx, sy)]))
        return faces

    @staticmethod
    def _octagon(side, top):
        (sx_, sy_, z), (tx, ty, _z) = side, top
        return [(sx_, -sy_, z), (sx_, sy_, z), (tx, ty, z), (-tx, ty, z), (-sx_, sy_, z), (-sx_, -sy_, z),
                (-tx, -ty, z), (tx, -ty, z)]

    def throat_octagon(self):
        hp = self.horn_points()
        return self._octagon(hp["R"], hp["Q"])

    def front_octagon(self):
        s, t = self.roll_points()[-1]
        return self._octagon(s, t)

    def plug_cloud(self) -> np.ndarray:
        L = self.L
        pts = [(0.0, 0.0, L - self.s("plug_nose_d_mm"))]
        tx, td = self.s("plug_tip_x_mm"), L - self.s("plug_tip_d_mm")
        ty, tdz = self.s("plug_top_y_mm"), L - self.s("plug_top_d_mm")
        cx, cy = self.s("plug_corner_x_mm"), self.s("plug_corner_y_mm")
        cz = L - self.plug_corner_d()
        bz = -self.plug_base_back_mm
        bx, bsy = self.s("plug_base_x_mm"), self.s("plug_base_side_y_mm")
        btx, by = self.s("plug_base_top_x_mm"), self.s("plug_base_y_mm")
        for sx in (1, -1):
            pts.append((sx * tx, 0.0, td))
        for sy in (1, -1):
            pts.append((0.0, sy * ty, tdz))
            for sx in (1, -1):
                pts += [(sx * cx, sy * cy, cz), (sx * bx, sy * bsy, bz), (sx * btx, sy * by, bz)]
        uniq = []
        for q in pts:                      # a zero side-height base is a hexagon: drop the duplicates
            if all(math.dist(q, u) > 0.5 for u in uniq):
                uniq.append(q)
        return np.array(uniq, dtype=float)

    def plug_corner_d(self) -> float:
        """Corner depth that puts nose, tip, ridge end and corner on ONE plane (as in the CAD: 258.8 mm on
        the Evo 7SH, recovered to 0.01 mm), so each front face of the axe head is a single flat plane."""
        L = self.L
        N = np.array([0.0, 0.0, L - self.s("plug_nose_d_mm")])
        T = np.array([self.s("plug_tip_x_mm"), 0.0, L - self.s("plug_tip_d_mm")])
        R = np.array([0.0, self.s("plug_top_y_mm"), L - self.s("plug_top_d_mm")])
        n = np.cross(T - N, R - N)
        cz = N[2] - (n[0] * self.s("plug_corner_x_mm") + n[1] * self.s("plug_corner_y_mm")) / n[2]
        return float(L - cz)

    # ------------------------------------------------------------------ checks
    def validate(self) -> None:
        for f in fields(self):
            if f.name.startswith("m_"):
                if getattr(self, f.name) < 0.0:
                    raise ValueError(f"{f.name} must be >= 0 (0 = off)")
                continue
            if f.name not in ("roll_steps", "plug_base_side_y_mm") and not getattr(self, f.name) > 0.0:
                raise ValueError(f"{f.name} must be > 0, got {getattr(self, f.name)}")
        if not 1 <= int(self.roll_steps) <= 8:
            raise ValueError("roll_steps must be in [1, 8]")
        g = self.s
        if not (g("throat_top_half_mm") < g("throat_side_x_mm") and g("throat_side_half_mm") < g("throat_top_y_mm")):
            raise ValueError("throat octagon: top half-length < side x and side half-height < top y")
        if not (g("mouth_top_half_mm") < g("mouth_side_x_mm") and g("mouth_side_half_mm") < g("mouth_top_y_mm")):
            raise ValueError("mouth: top half-length < side x and side half-height < top y")
        if not (g("throat_side_x_mm") < g("mouth_side_x_mm") < g("front_side_x_mm")
                and g("throat_top_y_mm") < g("mouth_top_y_mm") < g("front_top_y_mm")):
            raise ValueError("the horn must widen throat -> wall end -> front opening")
        if not (g("mouth_side_d_mm") < 0.3 * self.L and g("mouth_top_d_mm") < 0.3 * self.L):
            raise ValueError("the roll-out depths must be < 30 % of the length")
        oct_r = max(math.hypot(x, y) for x, y, _ in self.throat_octagon())
        if not oct_r < self.cone_r_mm:
            raise ValueError(f"the throat octagon (r {oct_r:.0f}) must sit inside the cone chamber (r {self.cone_r_mm})")
        if not self.post_r_mm < 0.4 * self.cone_r_mm:
            raise ValueError("post_r_mm must be < 0.4 * cone_r_mm")
        r_at_cone = g("bowl_r1_mm") - (g("bowl_r1_mm") - g("bowl_r2_mm")) * min(
            1.0, (self.front_gap_mm + self.cone_depth_mm) / g("bowl_len_mm"))
        if not (g("bowl_r1_mm") > self.cone_r_mm + 2 * self.wall_mm and r_at_cone > self.cone_r_mm + self.wall_mm
                and g("bowl_back_d_mm") > self.front_gap_mm + self.cone_depth_mm + self.wall_mm
                and g("bowl_len_mm") < g("bowl_back_d_mm")):
            raise ValueError("the driver bowl must enclose the cone chamber and the cone")
        if not (g("shell_w_mm") <= g("plate_w_mm") and g("shell_h_mm") <= g("plate_h_mm")
                and g("shell_w_mm") > 2 * g("front_side_x_mm") and g("shell_h_mm") > 2 * g("front_top_y_mm")):
            raise ValueError("shell must sit between the front opening and the plate edge")
        if not (g("plug_nose_d_mm") < g("plug_tip_d_mm") < self.L and g("plug_nose_d_mm") < g("plug_top_d_mm") < self.L
                and 0.0 < self.plug_corner_d() < self.L):
            raise ValueError("axe head: the nose must be the forward-most point and all points inside the horn")
        if not (g("plug_base_y_mm") > self.post_r_mm + 2 and g("plug_base_x_mm") > self.post_r_mm + 2):
            raise ValueError("the axe-head base must enclose the post (+2 mm)")
        clear = self.clearance()
        if clear["min_mm"] < self.plug_gap_mm:
            raise ValueError(
                f"axe-head clearance {clear['min_mm']:.1f} mm < plug_gap_mm {self.plug_gap_mm} "
                f"(at z = {clear['at_z_mm']:.0f} mm, against the {clear['against']})")

    def horn_section(self, z: float):
        """Convex cross-section of the air path at z (horn, or the round cone chamber behind the throat)."""
        if z >= 0.0:
            pts = []
            for kind, face in self.horn_faces():
                for poly in (_ruled_strips(face) if kind == "ruled" else [face]):
                    pts += _plane_cuts(poly, z)
            return _hull2d(pts) if len(pts) >= 3 else None
        ang = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        return self.cone_r_mm * np.c_[np.cos(ang), np.sin(ang)]

    def cone_z(self, r: float) -> float:
        t = (r - self.post_r_mm) / (self.cone_r_mm - self.post_r_mm)
        return -self.front_gap_mm - self.cone_depth_mm * (1.0 - min(max(t, 0.0), 1.0))

    def clearance(self, n: int = 200) -> dict[str, Any]:
        cloud = self.plug_cloud()
        edges = _hull_edges(cloud)
        z0, z1 = cloud[:, 2].min(), cloud[:, 2].max()
        best = {"min_mm": float("inf"), "at_z_mm": None, "against": None}
        for i in range(n + 1):
            z = z0 + (z1 - z0) * i / n
            sec = _edge_cuts(cloud, edges, z)
            if not sec:
                continue
            horn = self.horn_section(z)
            if horn is None or len(horn) < 3:               # the axe head reaches past the horn
                return {"min_mm": float("-inf"), "at_z_mm": z, "against": "outside of the horn"}
            for q in sec:
                d = _dist_inside(horn, q)
                if z < 0.0:
                    d = min(d, z - self.cone_z(math.hypot(*q)))
                if d < best["min_mm"]:
                    best = {"min_mm": d, "at_z_mm": z, "against": "horn wall" if z >= 0 else "cone chamber"}
        return best

    def rear_chamber_l(self) -> float:
        """Gross air volume inside the bowl behind the cone (driver motor/basket NOT subtracted)."""
        t = self.wall_mm
        r1, r2, rb = self.s("bowl_r1_mm") - t, self.s("bowl_r2_mm") - t, self.s("bowl_back_r_mm") - t
        l1 = self.s("bowl_len_mm")
        l2 = self.s("bowl_back_d_mm") - l1 - t
        v = math.pi * (l1 * (r1 * r1 + r1 * r2 + r2 * r2) / 3 + l2 * (r2 * r2 + r2 * rb + rb * rb) / 3)
        front = math.pi * self.front_gap_mm * self.cone_r_mm ** 2 + math.pi * self.cone_depth_mm * (
            self.cone_r_mm ** 2 + self.cone_r_mm * self.post_r_mm + self.post_r_mm ** 2) / 3
        return (v - front) / 1e6

    def derived(self) -> dict[str, Any]:
        L = self.L
        sd = math.pi * (self.cone_r_mm ** 2 - self.post_r_mm ** 2)
        cloud = self.plug_cloud()
        edges = _hull_edges(cloud)
        areas = []
        for i in range(0, 161):
            z = L * i / 160
            sec = _edge_cuts(cloud, edges, z)
            a_p = _poly_area(_hull2d(sec)) if len(sec) >= 3 else 0.0
            hs = self.horn_section(z)
            if hs is None or len(hs) < 3:                   # a degenerate cut (e.g. exactly at the front face)
                continue
            areas.append((z, _poly_area(hs) - a_p))
        zmin, amin = min(areas, key=lambda t: t[1])
        hp = self.horn_points()
        return {
            "sd_cm2": round(sd / 100, 1),
            "throat_area_cm2": round(_poly_area(np.array([(x, y) for x, y, _ in self.throat_octagon()])) / 100, 1),
            "min_channel_area_cm2": round(amin / 100, 1),
            "min_channel_depth_mm": round(L - zmin, 1),
            "compression_ratio": round(sd / amin, 2) if amin > 0 else float("inf"),
            "side_wall_angle_deg": round(math.degrees(math.atan2(hp["Ms"][0] - hp["R"][0], hp["Ms"][2])), 1),
            "top_wall_angle_deg": round(math.degrees(math.atan2(hp["Mt"][1] - hp["Q"][1], hp["Mt"][2])), 1),
            "front_opening_mm": [round(2 * self.s("front_side_x_mm"), 1), round(2 * self.s("front_top_y_mm"), 1)],
            "plug_width_frac_of_opening": round(self.s("plug_tip_x_mm") / self.s("front_side_x_mm"), 3),
            "outer_w_mm": round(self.s("plate_w_mm"), 1),
            "outer_h_mm": round(self.s("plate_h_mm"), 1),
            "depth_total_mm": round(L + self.s("bowl_back_d_mm"), 1),
            "rear_chamber_gross_l": round(self.rear_chamber_l(), 2),
            "plug_clearance_mm": round(float(self.clearance()["min_mm"]), 2),
            **self.theory(amin),
        }

    def theory(self, ring_area_mm2: float) -> dict[str, Any]:
        """Horn-theory diagnostics (estimates, for steering a search; the BEM is the judge).

        * K-law pattern control: a wall pair holds its angle down to f ~ 25.4e6 / (mouth mm * angle deg)
          (Keele; the repo's K-law), with the nominal angle = 2 x the wall angle.
        * mouth cut-off: the mouth stops loading the throat below ~ c / perimeter.
        * front-chamber cut-off: the air between cone and throat (V1) in parallel with the ring's
          radiation resistance: f ~ c * S_ring / (2 pi V1) [first-order; Keele's form, verify].
        * path spread: cone rim vs cone centre distance to the throat ring; the quarter-wave frequency
          c / (4 * spread) is where they start to cancel (the axe head's job is to keep this high).
        """
        c = 343.0e3                                          # mm/s
        fsx, fty = self.s("front_side_x_mm"), self.s("front_top_y_mm")
        hp = self.horn_points()
        ah = math.degrees(math.atan2(hp["Ms"][0] - hp["R"][0], hp["Ms"][2]))
        av = math.degrees(math.atan2(hp["Mt"][1] - hp["Q"][1], hp["Mt"][2]))
        g, cd, cr, pr = self.front_gap_mm, self.cone_depth_mm, self.cone_r_mm, self.post_r_mm
        v1 = math.pi * cr * cr * g + math.pi * cd * (cr * cr + cr * pr + pr * pr) / 3 - math.pi * pr * pr * cd
        r_ring = 0.5 * (self.s("throat_side_x_mm") + self.s("plug_base_x_mm"))
        rim = math.hypot(cr - r_ring, g)
        centre = math.hypot(r_ring - pr, g + cd)
        spread = abs(centre - rim)
        return {
            "k_law_pattern_h_hz": round(25.4e6 / (2 * fsx * 2 * ah), 0),
            "k_law_pattern_v_hz": round(25.4e6 / (2 * fty * 2 * av), 0),
            "mouth_cutoff_hz": round(c / (4 * (fsx + fty)), 0),
            "front_chamber_fc_hz": round(c * ring_area_mm2 / (2 * math.pi * v1), 0),
            "path_spread_mm": round(spread, 1),
            "path_quarter_wave_hz": round(c / (4 * spread), 0) if spread > 0 else None,
        }


# ---------------------------------------------------------------------- geometry helpers


def _plane_cuts(poly, z):
    out = []
    n = len(poly)
    for i in range(n):
        a, b = np.asarray(poly[i], dtype=float), np.asarray(poly[(i + 1) % n], dtype=float)
        if (a[2] - z) * (b[2] - z) <= 0 and a[2] != b[2]:
            t = (z - a[2]) / (b[2] - a[2])
            out.append(tuple((a + t * (b - a))[:2]))
        elif a[2] == z:
            out.append(tuple(a[:2]))
    return out


def _ruled_strips(q, n: int = 12):
    a, b, c, d = (np.asarray(v, dtype=float) for v in q)
    out = []
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        out.append([tuple(a + t0 * (b - a)), tuple(a + t1 * (b - a)), tuple(d + t1 * (c - d)), tuple(d + t0 * (c - d))])
    return out


def _hull_edges(cloud):
    from scipy.spatial import ConvexHull
    h = ConvexHull(cloud)
    e = set()
    for s in h.simplices:
        for i in range(3):
            e.add(tuple(sorted((int(s[i]), int(s[(i + 1) % 3])))))
    return sorted(e)


def _edge_cuts(cloud, edges, z):
    out = []
    for a, b in edges:
        pa, pb = cloud[a], cloud[b]
        if (pa[2] - z) * (pb[2] - z) <= 0 and pa[2] != pb[2]:
            t = (z - pa[2]) / (pb[2] - pa[2])
            out.append(tuple((pa + t * (pb - pa))[:2]))
    return out


def _hull2d(pts):
    from scipy.spatial import ConvexHull
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 3:
        return pts
    try:
        return pts[ConvexHull(pts).vertices]
    except Exception:  # noqa: BLE001 - degenerate section
        return pts


def _poly_area(pts) -> float:
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 3:
        return 0.0
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _dist_inside(poly, q) -> float:
    poly = np.asarray(poly, dtype=float)
    x, y = poly[:, 0], poly[:, 1]
    if float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) < 0:
        poly = poly[::-1]
    best = float("inf")
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if ln < 1e-9:                                   # repeated vertex: no edge
            continue
        best = min(best, ((q[0] - x0) * (-dy) + (q[1] - y0) * dx) / ln)
    return best


DEFAULTS = PlughornParams()
KEYS = tuple(f.name for f in fields(PlughornParams))
INT_KEYS = ("roll_steps",)


def params_from_recipe(recipe: dict) -> PlughornParams:
    values = {k: v for k, v in recipe.items() if k != "tool"}
    unknown = sorted(set(values) - set(KEYS))
    if unknown:
        raise ValueError(f"unknown plughorn key(s) {unknown}")
    p = replace(DEFAULTS, **{k: (int(round(float(v))) if k in INT_KEYS else float(v)) for k, v in values.items()})
    p = p.resolve_morph()
    p.validate()
    return p


# ---------------------------------------------------------------------- CAD


def _poly_face(bd, pts):
    return bd.Face(bd.Wire.make_polygon([bd.Vector(*p) for p in pts], close=True))


def _ruled_face(bd, q):
    a, b, c, d = (bd.Vector(*v) for v in q)
    return bd.Face.make_surface_from_curves(bd.Edge.make_line(a, b), bd.Edge.make_line(d, c))


def _convex_solid(bd, cloud):
    """Convex polyhedron of a point cloud; coplanar hull triangles merged into planar polygon faces."""
    from scipy.spatial import ConvexHull
    h = ConvexHull(cloud)
    groups: list[tuple[np.ndarray, set[int]]] = []
    for eq, simp in zip(h.equations, h.simplices):
        for g in groups:
            if np.allclose(g[0], eq, atol=1e-6):
                g[1].update(int(i) for i in simp)
                break
        else:
            groups.append((eq, set(int(i) for i in simp)))
    faces = []
    for eq, idx in groups:
        pts = cloud[sorted(idx)]
        nrm = np.asarray(eq[:3])
        c = pts.mean(axis=0)
        u = np.cross(nrm, [0, 0, 1.0]) if abs(nrm[2]) < 0.9 else np.cross(nrm, [1.0, 0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(nrm, u)
        ang = np.arctan2((pts - c) @ v, (pts - c) @ u)
        faces.append(_poly_face(bd, [tuple(p) for p in pts[np.argsort(ang)]]))
    return bd.Solid(bd.Shell(faces))


def build_body(p: PlughornParams = DEFAULTS):
    """Horn + front plate + shell + driver bowl + post + axe head as ONE closed solid (mm)."""
    p.validate()
    bd = _multicell()._cad()["bd"]
    L, over = p.L, 30.0

    # --- air: cone cavity + round compression chamber + horn + a prism past the front face
    g, cd = p.front_gap_mm, p.cone_depth_mm
    cavity = bd.revolve(bd.make_face(bd.Plane.XZ * bd.Polyline(
        (p.post_r_mm, -g - cd), (p.cone_r_mm, -g), (p.cone_r_mm, 0.0), (p.post_r_mm, 0.0), close=True)),
        bd.Axis.Z, 360)
    walls = [_poly_face(bd, f) if k == "plane" else _ruled_face(bd, f) for k, f in p.horn_faces()]
    horn = bd.Solid(bd.Shell(walls + [_poly_face(bd, p.throat_octagon()), _poly_face(bd, p.front_octagon())]))
    fo = p.front_octagon()
    prism = bd.loft([_poly_face(bd, fo), _poly_face(bd, [(x, y, z + over) for x, y, z in fo])], ruled=True)
    core = cavity + horn + prism

    # --- outside: front plate + convex shell to the driver ring + moulded bowl
    pw, ph, pt = 0.5 * p.s("plate_w_mm"), 0.5 * p.s("plate_h_mm"), p.s("plate_t_mm")
    plate = bd.Pos(0, 0, L - 0.5 * pt) * bd.Box(2 * pw, 2 * ph, pt)
    sw, sh = 0.5 * p.s("shell_w_mm"), 0.5 * p.s("shell_h_mm")
    r1 = p.s("bowl_r1_mm")
    # the shell's ring sits 5 mm down inside the bowl (radius - 4): no coplanar sliver where they join
    rr = r1 - 4.0
    ring = [(rr * math.cos(a), rr * math.sin(a), -5.0) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    shell = _convex_solid(bd, np.array(ring + [(sx * sw, sy * sh, L - pt) for sx in (1, -1) for sy in (1, -1)]))
    l1, bdp = p.s("bowl_len_mm"), p.s("bowl_back_d_mm")
    bowl = bd.revolve(bd.make_face(bd.Plane.XZ * bd.Polyline(
        (0.0, 0.0), (r1, 0.0), (p.s("bowl_r2_mm"), -l1), (p.s("bowl_back_r_mm"), -bdp), (0.0, -bdp),
        close=True)), bd.Axis.Z, 360)
    body = (plate + shell + bowl) - core

    # --- post + axe head
    zb = -p.plug_base_back_mm
    post = bd.Pos(0, 0, 0.5 * (-g - cd - 2.0 + zb + 2.0)) * bd.Cylinder(p.post_r_mm, (zb + 2.0) - (-g - cd - 2.0))
    plug = _convex_solid(bd, p.plug_cloud())
    return body + post + plug


def _is_driver_face(face, p: PlughornParams) -> bool:
    """The cone: a conical face between the post edge and the cone rim."""
    bb = face.bounding_box()
    slant = math.hypot(p.cone_r_mm - p.post_r_mm, p.cone_depth_mm)
    area = math.pi * (p.cone_r_mm + p.post_r_mm) * slant
    gt = face.geom_type.name if hasattr(face.geom_type, "name") else str(face.geom_type)
    return gt == "CONE" and bb.max.Z <= -p.front_gap_mm + 1e-3 and math.isclose(face.area, area, rel_tol=1e-3)


def check_solid(part, p: PlughornParams) -> dict[str, Any]:
    o = _multicell()._cad()
    faces = list(part.faces())
    shells = []
    ex = o["TopExp_Explorer"](part.wrapped, o["TopAbs_SHELL"])
    while ex.More():
        shells.append(o["BRep_Tool"].IsClosed_s(ex.Current()))
        ex.Next()
    res = {"faces": len(faces), "solids": len(part.solids()), "volume_mm3": part.volume,
           "valid": bool(o["BRepCheck_Analyzer"](part.wrapped).IsValid()), "shells": len(shells),
           "all_shells_closed": bool(shells) and all(shells),
           "driver_faces": sum(1 for f in faces if _is_driver_face(f, p)),
           "min_face_area_mm2": min(f.area for f in faces)}
    if res["solids"] != 1:
        raise RuntimeError(f"refusing: expected 1 solid, got {res['solids']}")
    if not res["valid"]:
        raise RuntimeError("refusing: the built solid is not a valid BRep")
    if not res["all_shells_closed"]:
        raise RuntimeError(f"refusing: {res['shells']} shell(s), not all closed")
    if res["driver_faces"] != 1:
        raise RuntimeError(f"refusing: {res['driver_faces']} candidate driver faces (need 1)")
    return res


def export(path: Path, p: PlughornParams = DEFAULTS) -> dict[str, Any]:
    mc = _multicell()
    part = build_body(p)
    solid = check_solid(part, p)
    labels = [(f, mc.DRIVER_LABEL if _is_driver_face(f, p) else mc.WALL_LABEL) for f in part.faces()]
    mc.write_labelled_step(part, labels, path)
    try:
        inventory = mc.read_face_inventory(path)
    except RuntimeError:
        Path(path).unlink(missing_ok=True)
        raise
    if sum(inventory.values()) != solid["faces"]:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError("refusing: STEP label count differs from the solid's faces")
    return {"params": p, "derived": p.derived(), "solid": solid, "part": part,
            "inventory": inventory, "path": Path(path)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="plughorn.py", description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="STEP path")
    ap.add_argument("--stl", help="also write an STL (quick look / print)")
    for f in fields(PlughornParams):
        ap.add_argument("--" + f.name.replace("_", "-"), type=type(f.default), default=f.default)
    a = ap.parse_args(argv)
    p = PlughornParams(**{f.name: getattr(a, f.name) for f in fields(PlughornParams)}).resolve_morph()
    res = export(Path(a.out), p)
    if a.stl:
        _multicell()._cad()["bd"].export_stl(res["part"], a.stl)
    print(res["derived"])
    print("solid:", res["solid"], "labels:", res["inventory"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
