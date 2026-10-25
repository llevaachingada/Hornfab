"""Multicell (WE/Altec-style) horn AIR volume -> STEP with named faces.

WP14, report 2 section 5.  This is a *tool*, not library code: every horn
number below is a documented default of this command, and every one of them is
a CLI argument.  Nothing here is imported by ``hornlab_search`` (the mesh
adapter is a later lane).

Geometry
--------
The air volume is ONE closed solid in millimetres, apex (virtual) at the
origin, +z toward the mouth, mirror-symmetric about ``x = 0`` and ``y = 0``:

* Cells are frusta of pyramids sharing the virtual apex at ``z = 0``.  With
  ``n_h`` cells the horizontal cell boundaries sit on the planes
  ``x = z * tan(alpha_i)`` with ``alpha_i = -alpha/2 + i * alpha / n_h``,
  ``i = 1 .. n_h-1``; the vertical ones on ``y = z * tan(beta_j)`` likewise.
  Every septum therefore contains the apex line, exactly as the classic
  WE/Altec cells do.  An ODD ``n_h``/``n_v`` leaves a cell centred on the
  axis (the axis runs through air, not through a septum).
* The outer body is the rectangular-sector horn: its walls are the planes
  ``x = +-z*tan(alpha/2)``, ``y = +-z*tan(beta/2)`` between the split ``z_s``
  and the flat mouth at ``z = L``.  Mouths therefore tile a rectangle (the
  "rectangular-sector outer body" option of report 2 section 5).
* The throat is exponential *from a manifold*: below ``z_s`` the section
  follows ``r(z) = r_throat * exp(m*z/2)`` (area law ``A(z) = A0*exp(m*z)``)
  with ``m = 4*pi*f_c/c`` from ``flare_hz``, and then adapts linearly to the
  rectangular split section at ``z_s``.  The flat rear face is the round
  driver exit, a disk of radius ``r_throat`` labelled ``driver``.
  Consequence (measured, see ``DERIVED`` in the CLI output): with a straight
  cell fan the flare rate cannot also shape the cell walls -- a plane septum
  requires walls proportional to ``z`` -- so ``flare_hz`` shapes the throat
  manifold and the cell fan is conical, as in the historical cells.
* Septa are thickened plates of ``septum_mm`` measured perpendicular to their
  plane, from ``z_s`` to the mouth.  ``septum_mm`` below 1.5 mm is refused:
  the solver's open-edge guard wants closed surfaces, and zero-thickness
  septa are not allowed (report 2 section 5, trap 1).
* ``throat_wall_mm`` is a *clearance constraint*, not modelled material: the
  export is the air volume, whose walls the solver treats as rigid.  The tool
  refuses a split section that leaves less than ``throat_wall_mm`` between the
  round throat bore and the cell walls (``min(X_s, Y_s) >= r_throat + wall``).

Face-label contract (pinned for the mesher adapter lane)
--------------------------------------------------------
Every face of the exported solid carries EXACTLY one label from
``{"driver", "wall"}`` (lowercase): the single throat/source face is
``driver``; the outer shell, both faces of every septum and the septum edge
caps, the manifold wall and the mouth are ``wall``.  The tool prints the
label -> count inventory of the *round-tripped* STEP and refuses to leave a
STEP whose inventory is empty or missing ``driver``.

Why not ``build123d.export_step``
---------------------------------
Verified against build123d 0.13.0 / OCC 8.0 on 2026-10-25: its XCAF writer
puts a shape name into ``PRODUCT`` and a colour's name into
``DRAUGHTING_PRE_DEFINED_COLOUR``/``PRESENTATION_LAYER_ASSIGNMENT`` only.
``SHELL_BASED_SURFACE_MODEL`` comes out unnamed and every presentation style
is ``STYLED_ITEM('color', ...)``; a sub-shape name is never written.  None of
that is readable by ``hornlab_mesher.step_text``, so ``export_step`` cannot
carry the contract.  This module therefore drives OCC's *own* STEP writer
(``STEPControl_Writer`` + ``STEPConstruct_Styles``) and gives each face a
presentation style named after its label:
``STYLED_ITEM('driver', (#psa), #face)``.  That is the standard
presentation-label mechanism the pinned contract names; no STEP text is
rewritten and no entity is hand-serialised.

Usage
-----
    .venv\\Scripts\\python.exe tools\\cad\\multicell.py \\
        --out runs\\m5_wp14\\multicell_3x3.step

Every parameter has a documented default (see ``DEFAULTS``); the documented
default configuration is the 3x3 horn printed by ``--help``.
"""

from __future__ import annotations

import argparse
import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------- constants

SPEED_OF_SOUND_M_PER_S = 343.0
"""Dry air at 20 C.  Fixed here because the tool has no ambient model."""

MIN_SEPTUM_MM = 1.5
"""Solver constraint: closed surfaces only, so septa need finite thickness."""

DRIVER_LABEL = "driver"
WALL_LABEL = "wall"
LABELS = (DRIVER_LABEL, WALL_LABEL)

_EPS_MM = 1.0e-6
_PLATE_OVERRUN_MM = 20.0
"""How far a septum plate is extended past the mouth before trimming."""

_DRIVER_COLOUR = (0.37, 0.53, 0.71)
_WALL_COLOUR = (0.61, 0.47, 0.29)
"""Arbitrary RGB values: matching an ISO predefined colour would add a second
string (e.g. 'red') to the presentation style, and ``step_text`` reads those
too -- the label set must stay exactly {'driver', 'wall'}."""


# ---------------------------------------------------------------- parameters


@dataclass(frozen=True)
class MulticellParams:
    """The tool's own parameters, all millimetres / degrees.

    These are the documented defaults; the example config the mesh-adapter
    lane writes must use the same numbers (the CLI prints them on every run).
    """

    n_h: int = 3
    """Horizontal cells (an odd count centres a cell on the axis)."""
    n_v: int = 3
    """Vertical cells (an odd count centres a cell on the axis)."""
    alpha_total_deg: float = 60.0
    """Total horizontal cap angle of the cell fan, at the split plane."""
    beta_total_deg: float = 40.0
    """Total vertical cap angle of the cell fan, at the split plane."""
    length_mm: float = 300.0
    """Axial length from the driver face to the mouth."""
    z_s_mm: float = 60.0
    """Where the single throat splits into cells (septum start)."""
    r_throat_mm: float = 12.7
    """Radius of the round driver exit face (25.4 mm = 1 inch diameter)."""
    septum_mm: float = 2.0
    """Septum thickness, measured perpendicular to the septum plane."""
    throat_wall_mm: float = 3.0
    """Minimum material between the throat bore and the cell walls."""
    flare_hz: float = 200.0
    """Exponential flare cutoff of the throat manifold (0 = cylindrical)."""

    def validate(self) -> None:
        """Raise ``ValueError`` for a configuration this tool refuses to build."""
        if int(self.n_h) != self.n_h or int(self.n_v) != self.n_v:
            raise ValueError(f"n_h/n_v must be integers, got {self.n_h!r}/{self.n_v!r}")
        if self.n_h < 1 or self.n_v < 1:
            raise ValueError(f"n_h and n_v must be >= 1, got {self.n_h} and {self.n_v}")
        if not (0.0 < self.alpha_total_deg < 180.0):
            raise ValueError(
                f"alpha_total_deg must be in (0, 180), got {self.alpha_total_deg}")
        if not (0.0 < self.beta_total_deg < 180.0):
            raise ValueError(
                f"beta_total_deg must be in (0, 180), got {self.beta_total_deg}")
        if not self.r_throat_mm > 0.0:
            raise ValueError(f"r_throat_mm must be positive, got {self.r_throat_mm}")
        if not (0.0 < self.z_s_mm < self.length_mm):
            raise ValueError(
                "septum start must satisfy 0 < z_s < length, got "
                f"z_s={self.z_s_mm} mm, length={self.length_mm} mm")
        if self.septum_mm < MIN_SEPTUM_MM:
            raise ValueError(
                f"refusing septum_mm={self.septum_mm} mm: the closed-surface solver "
                f"contract needs >= {MIN_SEPTUM_MM} mm")
        if not self.throat_wall_mm > 0.0:
            raise ValueError(
                f"throat_wall_mm must be positive, got {self.throat_wall_mm}")
        if self.flare_hz < 0.0:
            raise ValueError(f"flare_hz must be >= 0, got {self.flare_hz}")
        derived = self.derived()
        # The split section is half the outer body's cross-section; a round
        # throat plus the requested wall has to fit inside it.
        if min(derived["X_s_mm"], derived["Y_s_mm"]) < (
            self.r_throat_mm + self.throat_wall_mm
        ):
            raise ValueError(
                f"throat_wall_mm={self.throat_wall_mm} mm does not fit: the split "
                f"section is {derived['X_s_mm']:.2f} x {derived['Y_s_mm']:.2f} mm "
                f"half-extents, the throat bore needs r={self.r_throat_mm} + "
                f"{self.throat_wall_mm} mm")
        for cells, half_deg in (
            (self.n_h, self.alpha_total_deg / 2.0),
            (self.n_v, self.beta_total_deg / 2.0),
        ):
            if cells > 1:
                gap = self.z_s_mm * math.sin(math.radians(half_deg / cells))
                if gap <= self.septum_mm:
                    raise ValueError(
                        f"{cells} cells across {2 * half_deg:g} deg leave {gap:.3f} mm "
                        f"between septum planes at z_s={self.z_s_mm} mm, which is not "
                        f"more than septum_mm={self.septum_mm} mm")

    def derived(self) -> dict[str, Any]:
        """Derived geometry, printed by the CLI and asserted by the tests."""
        m_per_mm = 4.0 * math.pi * self.flare_hz / (SPEED_OF_SOUND_M_PER_S * 1000.0)
        alpha = math.radians(self.alpha_total_deg)
        beta = math.radians(self.beta_total_deg)
        x_s = self.z_s_mm * math.tan(alpha / 2.0)
        y_s = self.z_s_mm * math.tan(beta / 2.0)
        z_mid = 0.5 * self.z_s_mm
        h_deg = [
            math.degrees(-alpha / 2.0 + i * alpha / self.n_h)
            for i in range(1, self.n_h)
        ]
        v_deg = [
            math.degrees(-beta / 2.0 + j * beta / self.n_v)
            for j in range(1, self.n_v)
        ]
        return {
            "flare_m_per_mm": m_per_mm,
            "r_at_split_mm": self.r_throat_mm * math.exp(m_per_mm * self.z_s_mm / 2.0),
            "r_at_adapter_mm": self.r_throat_mm * math.exp(m_per_mm * z_mid / 2.0),
            "adapter_start_mm": z_mid,
            "X_s_mm": x_s,
            "Y_s_mm": y_s,
            "X_mouth_mm": self.length_mm * math.tan(alpha / 2.0),
            "Y_mouth_mm": self.length_mm * math.tan(beta / 2.0),
            "h_septum_deg": h_deg,
            "v_septum_deg": v_deg,
        }

    def summary(self) -> str:
        d = self.derived()
        h = ", ".join(f"{a:+.4f}" for a in d["h_septum_deg"]) or "(none)"
        v = ", ".join(f"{b:+.4f}" for b in d["v_septum_deg"]) or "(none)"
        return (
            f"n_h={self.n_h} n_v={self.n_v} "
            f"alpha_total={self.alpha_total_deg:g} deg beta_total={self.beta_total_deg:g} deg "
            f"length={self.length_mm:g} mm z_s={self.z_s_mm:g} mm "
            f"r_throat={self.r_throat_mm:g} mm septum={self.septum_mm:g} mm "
            f"throat_wall={self.throat_wall_mm:g} mm flare={self.flare_hz:g} Hz "
            f"(m={d['flare_m_per_mm']:.6f} 1/mm)\n"
            f"  H septa at {h} deg; V septa at {v} deg\n"
            f"  split section {2 * d['X_s_mm']:.2f} x {2 * d['Y_s_mm']:.2f} mm, "
            f"mouth {2 * d['X_mouth_mm']:.2f} x {2 * d['Y_mouth_mm']:.2f} mm"
        )


DEFAULTS = MulticellParams()
"""The documented default configuration: a 3x3 multicell (see ``--help``)."""


# ---------------------------------------------------------------- CAD bridge


def _cad():  # pragma: no cover - exercised by every test that builds a solid
    """Import build123d/OCP on use, so the module still imports without it."""
    try:
        import build123d as bd
        from OCP.BRep import BRep_Tool
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
        from OCP.STEPConstruct import STEPConstruct_RenderingProperties, STEPConstruct_Styles
        from OCP.STEPControl import STEPControl_StepModelType, STEPControl_Writer
        from OCP.StepVisual import StepVisual_PresentationStyleAssignment
        from OCP.TCollection import TCollection_HAsciiString
        from OCP.TopAbs import TopAbs_SHELL
        from OCP.TopExp import TopExp_Explorer
        from OCP.collections import HArray1_StepVisual_PresentationStyleSelect
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "this tool needs build123d; install the optional extra: "
            "`.venv\\Scripts\\python.exe -m pip install -e .[cad]`"
        ) from exc
    return {
        "bd": bd,
        "BRep_Tool": BRep_Tool,
        "BRepCheck_Analyzer": BRepCheck_Analyzer,
        "Quantity_Color": Quantity_Color,
        "Quantity_TypeOfColor": Quantity_TypeOfColor,
        "STEPConstruct_RenderingProperties": STEPConstruct_RenderingProperties,
        "STEPConstruct_Styles": STEPConstruct_Styles,
        "STEPControl_StepModelType": STEPControl_StepModelType,
        "STEPControl_Writer": STEPControl_Writer,
        "StepVisual_PresentationStyleAssignment": StepVisual_PresentationStyleAssignment,
        "TCollection_HAsciiString": TCollection_HAsciiString,
        "TopAbs_SHELL": TopAbs_SHELL,
        "TopExp_Explorer": TopExp_Explorer,
        "HArray1_StepVisual_PresentationStyleSelect": HArray1_StepVisual_PresentationStyleSelect,
    }


@contextmanager
def _quiet_occ():
    """Silence OCC's STEP writer banner for the duration of a transfer/write."""
    from OCP.Message import Message

    messenger = Message.DefaultMessenger_s()
    active = messenger.ChangePrinters()
    saved = [active.Value(i) for i in range(1, active.Length() + 1)]
    active.Clear()
    try:
        yield
    finally:
        for printer in saved:
            messenger.AddPrinter(printer)


def _plate(p: MulticellParams, angle_rad: float, *, horizontal: bool, extent_mm: float):
    """One thickened septum plate, long enough to be trimmed by the boolean."""
    o = _cad()
    bd = o["bd"]
    half = 0.5 * p.septum_mm
    tangent = math.tan(angle_rad)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    z0, z1 = p.z_s_mm, p.length_mm + _PLATE_OVERRUN_MM
    # Thickness measured along the plane normal, flat end cap at z_s.
    points = [
        (z0 * tangent - half * cos_a, z0),
        (z0 * tangent + half * cos_a, z0),
        (z1 * tangent + half * cos_a, z1 - half * sin_a),
        (z1 * tangent - half * cos_a, z1 + half * sin_a),
    ]
    plane = bd.Plane.XZ if horizontal else bd.Plane.YZ
    face = bd.make_face(plane * bd.Polyline(*points, close=True))
    return bd.extrude(
        face,
        amount=extent_mm + _PLATE_OVERRUN_MM,
        dir=(0, 1, 0) if horizontal else (1, 0, 0),
        both=True,
    )


def build_air_volume(p: MulticellParams = DEFAULTS):
    """Build the multicell air volume as ONE closed solid (millimetres).

    Sections, bottom to top: round driver exit -> exponential throat -> linear
    adapter -> rectangular split -> conical cell body -> flat mouth.  They are
    one ruled loft, so the whole envelope is a single solid before the septa
    are subtracted (no fuse seam at ``z_s``).
    """
    p.validate()
    o = _cad()
    bd = o["bd"]
    d = p.derived()

    envelope = bd.loft(
        [
            bd.Plane.XY * bd.Circle(p.r_throat_mm),
            bd.Plane.XY.offset(d["adapter_start_mm"]) * bd.Circle(d["r_at_adapter_mm"]),
            bd.Plane.XY.offset(p.z_s_mm) * bd.Rectangle(2 * d["X_s_mm"], 2 * d["Y_s_mm"]),
            bd.Plane.XY.offset(p.length_mm)
            * bd.Rectangle(2 * d["X_mouth_mm"], 2 * d["Y_mouth_mm"]),
        ],
        ruled=True,
    )

    air = envelope
    alpha = math.radians(p.alpha_total_deg)
    beta = math.radians(p.beta_total_deg)
    for i in range(1, p.n_h):
        air = air - _plate(
            p, -alpha / 2.0 + i * alpha / p.n_h, horizontal=True,
            extent_mm=d["Y_mouth_mm"],
        )
    for j in range(1, p.n_v):
        air = air - _plate(
            p, -beta / 2.0 + j * beta / p.n_v, horizontal=False,
            extent_mm=d["X_mouth_mm"],
        )
    return air


def _driver_area_mm2(p: MulticellParams) -> float:
    return math.pi * p.r_throat_mm * p.r_throat_mm


def _is_driver_face(face, p: MulticellParams) -> bool:
    """True for the flat round throat face: on the axis, facing -z, area pi r^2."""
    centre = face.center()
    return (
        abs(centre.Z) <= _EPS_MM
        and abs(face.normal_at(centre).Z) > 1.0 - 1.0e-9
        and math.isclose(face.area, _driver_area_mm2(p), rel_tol=1.0e-6)
    )


def check_solid(part, p: MulticellParams = DEFAULTS) -> dict[str, Any]:
    """Prove the solid is closed/manifold and find the single driver face."""
    o = _cad()
    faces = list(part.faces())
    if not faces:
        raise RuntimeError("refusing: the built solid has no faces")

    shells = []
    explorer = o["TopExp_Explorer"](part.wrapped, o["TopAbs_SHELL"])
    while explorer.More():
        shells.append(o["BRep_Tool"].IsClosed_s(explorer.Current()))
        explorer.Next()

    degenerate = [face for face in faces if face.area <= 0.0]
    drivers = [face for face in faces if _is_driver_face(face, p)]

    result = {
        "faces": len(faces),
        "solids": len(part.solids()),
        "volume_mm3": part.volume,
        "valid": bool(o["BRepCheck_Analyzer"](part.wrapped).IsValid()),
        "shells": len(shells),
        "all_shells_closed": bool(shells) and all(shells),
        "degenerate_faces": len(degenerate),
        "driver_faces": len(drivers),
        "min_face_area_mm2": min(face.area for face in faces),
    }
    if result["solids"] != 1:
        raise RuntimeError(f"refusing: expected 1 solid, got {result['solids']}")
    if not result["valid"]:
        raise RuntimeError("refusing: the built solid is not a valid BRep")
    if not result["all_shells_closed"]:
        raise RuntimeError(
            f"refusing: {result['shells']} shell(s), not all closed (open-edge guard)")
    if not result["volume_mm3"] > 0.0:
        raise RuntimeError(f"refusing: non-positive volume {result['volume_mm3']}")
    if result["degenerate_faces"]:
        raise RuntimeError(
            f"refusing: {result['degenerate_faces']} zero-area face(s); the STEP "
            "would not start clean")
    if result["driver_faces"] != 1:
        raise RuntimeError(
            f"refusing: {result['driver_faces']} candidate driver faces (need exactly 1)")
    return result


def face_labels(part, p: MulticellParams = DEFAULTS) -> list[tuple[Any, str]]:
    """Return ``(face, label)`` for every face of the solid."""
    return [
        (face, DRIVER_LABEL if _is_driver_face(face, p) else WALL_LABEL)
        for face in part.faces()
    ]


def write_labelled_step(part, labels: Iterable[tuple[Any, str]], path: Path) -> Path:
    """Write ``part`` as STEP with one named presentation style per face."""
    o = _cad()
    labels = list(labels)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    writer = o["STEPControl_Writer"]()
    with _quiet_occ():
        status = writer.Transfer(
            part.wrapped, o["STEPControl_StepModelType"].STEPControl_AsIs
        )
    if "RetDone" not in str(status):
        raise RuntimeError(f"refusing: STEP transfer failed ({status})")

    styles = o["STEPConstruct_Styles"]()
    styles.Init(writer.WS())
    model = writer.Model()
    colours = {
        DRIVER_LABEL: o["Quantity_Color"](*_DRIVER_COLOUR, o["Quantity_TypeOfColor"].Quantity_TOC_RGB),
        WALL_LABEL: o["Quantity_Color"](*_WALL_COLOUR, o["Quantity_TypeOfColor"].Quantity_TOC_RGB),
    }
    encoded = {
        label: o["STEPConstruct_Styles"].EncodeColor_s(colour)
        for label, colour in colours.items()
    }
    for face, label in labels:
        # AddStyle(shape, ...) resolves the face's ADVANCED_FACE through OCC's
        # finder process; the probe round-trip is how we get that entity.
        probe = styles.AddStyle(
            face.wrapped, o["StepVisual_PresentationStyleAssignment"](), None
        )
        if probe is None:
            raise RuntimeError("refusing: OCC could not map a face onto its STEP entity")
        item = probe.Item()
        colour = colours[label]
        psa_full = styles.MakeColorPSA(
            item,
            encoded[label],
            encoded[label],
            o["STEPConstruct_RenderingProperties"](colour),
            False,
        )
        # Keep only the surface style: the curve style carries the string
        # 'continuous' (DRAUGHTING_PRE_DEFINED_CURVE_FONT), which step_text
        # would read as a second label on that face.
        psa = o["StepVisual_PresentationStyleAssignment"]()
        styles_array = o["HArray1_StepVisual_PresentationStyleSelect"](1, 1)
        styles_array.SetValue(1, psa_full.Styles().Value(1))
        psa.SetStyles(styles_array)
        styled = styles.AddStyle(item, psa, None)
        styled.SetName(o["TCollection_HAsciiString"](label))
        model.AddWithRefs(styled)

    with _quiet_occ():
        status = writer.Write(str(path))
    if "RetDone" not in str(status):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"refusing: STEP write failed ({status})")
    return path


# ---------------------------------------------------------------- round trip


def step_text_module():
    """The pinned parser the mesher adapter lane builds against."""
    try:
        from hornlab_mesher import step_text
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "the label round-trip check needs hornlab_mesher.step_text "
            "(hornlab-waveguide-mesher is a main dependency of hornlab-search)"
        ) from exc
    return step_text


def read_face_inventory(path: Path) -> dict[str, int]:
    """Return the label -> face count of a written STEP, as ``step_text`` sees it.

    Raises ``RuntimeError`` when the file is not exactly one solid body whose
    faces each carry exactly one of :data:`LABELS`.
    """
    parser = step_text_module()
    path = Path(path)
    text = parser.read_step_text(path)

    bodies = parser.step_body_inventory(text)
    if len(bodies) != 1:
        raise RuntimeError(
            f"refusing: STEP has {len(bodies)} bodies, expected exactly 1 "
            f"({[b.entity for b in bodies]})")
    if bodies[0].kind != "solid":
        raise RuntimeError(f"refusing: STEP body is {bodies[0].kind}, not a solid")

    unit = parser.step_length_unit_mm_from_text(text)
    if unit is None or abs(unit - 1.0) > 1.0e-9:
        raise RuntimeError(f"refusing: STEP length unit is {unit} mm, expected 1.0")

    named = parser.parse_named_shell_faces(path)
    if named:
        raise RuntimeError(
            "refusing: unexpected named shell/surface bodies in the STEP: "
            f"{sorted(named)}")
    styled = parser.parse_styled_face_groups(path)

    per_face: dict[int, list[str]] = {}
    for label, face_ids in styled.items():
        if label not in LABELS:
            raise RuntimeError(
                f"refusing: STEP carries an unlabelled-group name {label!r}; "
                f"allowed labels are {list(LABELS)}")
        for face_id in face_ids:
            per_face.setdefault(face_id, []).append(label)

    solid_faces = parser.parse_solid_brep_faces(path)
    stray = set(per_face) - solid_faces
    unlabelled = solid_faces - set(per_face)
    if stray:
        raise RuntimeError(
            f"refusing: {len(stray)} labelled face(s) outside the solid body")
    if unlabelled:
        raise RuntimeError(
            f"refusing: {len(unlabelled)} of {len(solid_faces)} solid faces carry no label")
    doubled = {face: tags for face, tags in per_face.items() if len(tags) != 1}
    if doubled:
        raise RuntimeError(
            f"refusing: {len(doubled)} face(s) carry more than one label: "
            f"{list(doubled.items())[:3]}")
    if sum(1 for tags in per_face.values() if tags[0] == DRIVER_LABEL) != 1:
        raise RuntimeError(
            "refusing: STEP must carry exactly one 'driver' face, found "
            f"{sum(1 for tags in per_face.values() if tags[0] == DRIVER_LABEL)}")

    inventory = {label: 0 for label in LABELS}
    for tags in per_face.values():
        inventory[tags[0]] += 1
    inventory = {label: count for label, count in inventory.items() if count}
    if not inventory or DRIVER_LABEL not in inventory:
        raise RuntimeError(f"refusing: empty or driver-less face inventory {inventory}")
    return inventory


# ---------------------------------------------------------------- entry point


def export(path: Path, p: MulticellParams = DEFAULTS) -> dict[str, Any]:
    """Build, check, write, and round-trip one multicell STEP."""
    p.validate()
    part = build_air_volume(p)
    solid = check_solid(part, p)
    labels = face_labels(part, p)
    write_labelled_step(part, labels, path)
    try:
        inventory = read_face_inventory(path)
    except RuntimeError:
        # A STEP whose labels do not round-trip must never be left behind.
        Path(path).unlink(missing_ok=True)
        raise
    if sum(inventory.values()) != solid["faces"]:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(
            f"refusing: STEP labels {sum(inventory.values())} faces but the solid has "
            f"{solid['faces']}")
    return {"params": p, "derived": p.derived(), "solid": solid, "part": part,
            "inventory": inventory, "path": Path(path)}


def _parser() -> argparse.ArgumentParser:
    d = DEFAULTS
    parser = argparse.ArgumentParser(
        prog="multicell.py",
        description=(
            "Build a classic multicell horn AIR volume as one closed solid and "
            "export STEP with 'driver'/'wall' face labels."
        ),
        epilog="Documented default (3x3, WP14): "
        + " ".join(line.strip() for line in d.summary().splitlines()),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n-h", type=int, default=d.n_h, help="horizontal cells")
    parser.add_argument("--n-v", type=int, default=d.n_v, help="vertical cells")
    parser.add_argument("--alpha-total", type=float, default=d.alpha_total_deg,
                        help="total horizontal cap angle at the split [deg]")
    parser.add_argument("--beta-total", type=float, default=d.beta_total_deg,
                        help="total vertical cap angle at the split [deg]")
    parser.add_argument("--length", type=float, default=d.length_mm,
                        help="driver face to mouth [mm]")
    parser.add_argument("--z-s", type=float, default=d.z_s_mm,
                        help="septum start, where the throat splits [mm]")
    parser.add_argument("--r-throat", type=float, default=d.r_throat_mm,
                        help="driver exit radius [mm]")
    parser.add_argument("--septum", type=float, default=d.septum_mm,
                        help=f"septum thickness, minimum {MIN_SEPTUM_MM} [mm]")
    parser.add_argument("--throat-wall", type=float, default=d.throat_wall_mm,
                        help="material between throat bore and cell walls [mm]")
    parser.add_argument("--flare-hz", type=float, default=d.flare_hz,
                        help="exponential throat-manifold cutoff (0 = straight) [Hz]")
    parser.add_argument("--out", type=Path, required=True, default=argparse.SUPPRESS,
                        help="STEP output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    params = replace(
        DEFAULTS,
        n_h=args.n_h,
        n_v=args.n_v,
        alpha_total_deg=args.alpha_total,
        beta_total_deg=args.beta_total,
        length_mm=args.length,
        z_s_mm=args.z_s,
        r_throat_mm=args.r_throat,
        septum_mm=args.septum,
        throat_wall_mm=args.throat_wall,
        flare_hz=args.flare_hz,
    )
    print(f"multicell air volume: {params.summary()}")
    try:
        result = export(args.out, params)
    except (ValueError, RuntimeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    solid = result["solid"]
    print(
        f"solid: 1 solid, {solid['faces']} faces, valid={solid['valid']}, "
        f"closed={solid['all_shells_closed']}, volume={solid['volume_mm3']:.1f} mm^3, "
        f"min face area={solid['min_face_area_mm2']:.3f} mm^2"
    )
    inventory = result["inventory"]
    print("face inventory (round-tripped STEP): "
          + " ".join(f"{label}={count}" for label, count in sorted(inventory.items())))
    path = result["path"]
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
