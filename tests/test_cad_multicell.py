"""WP14: tools/cad/multicell.py - the multicell air volume and its face labels.

The tool is a script, not a package module, so it is loaded by path.  Loading it
does not import build123d (the CAD imports are lazy), which is why the whole
suite is gated on ``requires_build123d`` at the test level and not at import.

The label round-trip test is the cross-lane contract: the mesh adapter lane will
look up ``driver``/``wall`` with ``hornlab_mesher.step_text``, so the labels are
recovered here with those parsers and not with the tool's own view of the file.
"""

from __future__ import annotations

import importlib.util
import math
import sys

import pytest

from conftest import REPO, requires_build123d

TOOL = REPO / "tools" / "cad" / "multicell.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("cad_multicell_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


multicell = _load_tool()


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """One 3x3 default build + STEP export, shared by the read-only tests."""
    out = tmp_path_factory.mktemp("wp14") / "multicell_3x3.step"
    return multicell.export(out, multicell.DEFAULTS)


@requires_build123d
def test_default_3x3_builds_and_exports(run):
    """The documented 3x3 default builds one solid and writes a STEP file."""
    path = run["path"]
    assert path.is_file()
    assert path.stat().st_size > 10_000
    assert run["params"].n_h == 3 and run["params"].n_v == 3

    solid = run["solid"]
    assert solid["solids"] == 1
    assert solid["faces"] >= 2
    assert solid["volume_mm3"] > 0.0

    inventory = run["inventory"]
    assert inventory["driver"] == 1
    assert sum(inventory.values()) == solid["faces"]


@requires_build123d
def test_label_round_trip_is_exact(run):
    """Every STEP face carries exactly one label; exactly one is `driver`."""
    from hornlab_mesher import step_text

    path = run["path"]
    text = step_text.read_step_text(path)

    bodies = step_text.step_body_inventory(text)
    assert len(bodies) == 1, [body.entity for body in bodies]
    assert bodies[0].kind == "solid"

    # The tool uses presentation labels only: a named shell/surface body would
    # be a second label source and is not part of the contract.
    assert step_text.parse_named_shell_faces(path) == {}

    styled = step_text.parse_styled_face_groups(path)
    assert set(styled) == {"driver", "wall"}
    assert len(styled["driver"]) == 1

    per_face = {}
    for label, face_ids in styled.items():
        for face_id in face_ids:
            per_face.setdefault(face_id, []).append(label)
    assert all(len(labels) == 1 for labels in per_face.values())

    solid_faces = step_text.parse_solid_brep_faces(path)
    assert set(per_face) == solid_faces
    assert len(solid_faces) == run["solid"]["faces"]
    assert sum(1 for labels in per_face.values() if labels == ["driver"]) == 1


@requires_build123d
def test_solid_is_closed_and_manifold(run):
    """One valid closed shell, no zero-area faces, one driver face on the axis."""
    solid = run["solid"]
    assert solid["valid"] is True
    assert solid["solids"] == 1
    assert solid["shells"] == 1 and solid["all_shells_closed"] is True
    assert solid["degenerate_faces"] == 0
    assert solid["min_face_area_mm2"] > 0.0
    assert solid["driver_faces"] == 1

    # The driver face is the round throat: area pi*r^2, centre on the axis at z=0.
    params = run["params"]
    drivers = [
        (face, label)
        for face, label in multicell.face_labels(run["part"], params)
        if label == "driver"
    ]
    assert len(drivers) == 1
    face = drivers[0][0]
    assert face.area == pytest.approx(math.pi * params.r_throat_mm**2, rel=1.0e-6)
    centre = face.center()
    assert abs(centre.X) < 1.0e-6 and abs(centre.Y) < 1.0e-6
    assert abs(centre.Z) < 1.0e-6


@requires_build123d
def test_septum_thinner_than_minimum_is_refused():
    """t < 1.5 mm is refused on the build path; 1.5 mm is accepted."""
    thin = multicell.MulticellParams(septum_mm=1.4)
    with pytest.raises(ValueError, match=r"1\.5"):
        thin.validate()
    with pytest.raises(ValueError, match="septum_mm"):
        multicell.build_air_volume(thin)

    multicell.MulticellParams(septum_mm=1.5).validate()


@requires_build123d
def test_odd_cell_count_puts_a_cell_centre_on_the_axis(run):
    """For 3x3 the axis runs through the middle cell's air, not a septum."""
    from build123d import Vector

    params = run["params"]
    derived = params.derived()
    assert derived["h_septum_deg"] == pytest.approx([-10.0, 10.0])
    assert derived["v_septum_deg"] == pytest.approx([-20.0 / 3.0, 20.0 / 3.0])

    part = run["part"]
    for z in (params.z_s_mm + 1.0, 0.5 * (params.z_s_mm + params.length_mm),
              params.length_mm - 1.0):
        assert part.is_inside(Vector(0.0, 0.0, z)), f"axis blocked at z={z} mm"

    # The septa really do split the mouth: one mouth face per cell.
    def mouth_faces(p, part):
        return [
            face
            for face in part.faces()
            if abs(face.center().Z - p.length_mm) < 1.0e-6
            and face.normal_at(face.center()).Z > 1.0 - 1.0e-9
        ]

    assert len(mouth_faces(params, part)) == params.n_h * params.n_v

    # Complement: an EVEN count puts a septum on the axis, so the same point is
    # inside the septum material and therefore not inside the air volume.
    even = multicell.MulticellParams(n_h=2, n_v=3)
    even_part = multicell.build_air_volume(even)
    z_mid = 0.5 * (even.z_s_mm + even.length_mm)
    assert not even_part.is_inside(Vector(0.0, 0.0, z_mid))
    assert len(mouth_faces(even, even_part)) == even.n_h * even.n_v
