"""CAD (labelled STEP) -> .msh in METRES, through the pinned mesher's own STEP layer.

This is the **caller-side driver** the fork's ``docs/architecture.md`` describes
(151-162): the CAD tool authors the geometry, ``hornlab_mesher.step_mapping`` /
``mesh_repair`` / ``mesh_validation`` do the STEP reading, repairing and frequency
validation, and this module owns only the glue plus the same guards ``mesh/build.py``
runs. Nothing here writes a mesher, a STEP writer or a triangulation:

* the solid and the labelled STEP come from ``tools/cad/multicell.py`` (by file
  path, so the tool stays the single canonical builder);
* the STEP labels -> gmsh surfaces mapping is
  ``step_mapping.advanced_face_order_for_surfaces`` (geometry-matched, not record
  order) fed from ``step_text.parse_styled_face_groups``;
* the mesh repair/orientation is ``mesh_repair.postprocess_mesh``;
* the frequency report is ``mesh_validation.mesh_frequency_validation``;
* physical-group names/tags come from ``hornlab_mesher.tags`` (1 = SD1G0 rigid,
  2 = SD1D1001 source).

Route contract
--------------
``design.params["cad"]`` (a ``Design`` of family FREEFORM whose ONLY param is
``cad``) carries the recipe. The recipe is the single source of truth: the STEP is
**generated** per build into ``<out_dir>/cad/multicell.step`` -- never referenced
pre-built -- and its sha256 is echoed into ``mesh_meta.json``. The face-label
inventory of the round-tripped STEP (``{"driver": 1, "wall": N}``) is echoed too.

Resolution comes from the run's ``MeshSpec`` exactly as the formula and GRID routes
do it (``build.res_mm_for_spec``): ``res["mouth"]`` is the global gmsh target and
``res["throat"]`` (= mouth / 2, the mesher's own throat convention) refines the
region within ``SOURCE_TRANSITION_MM`` of the driver face. gmsh's maximum triangle
edge on an OCC surface runs ~1.4x the target size, and
``mesh_frequency_validation``'s limit is max-edge based; the graded target keeps the
driven patch valid at the recipe's ``f_max_hz`` and the adjacent-wall report honest
(see the frequency policy below).

Frequency policy (deliberately the mesher's, not a new one)
-----------------------------------------------------------
``mesh_frequency_validation`` is ``global_warn_source_hard``: coarse regions FAR
from the source are warnings, and only the driven patch hard-fails. This adapter
*refuses* (``GeometryInvalidError``) when the driver patch itself cannot resolve
``mesh_spec.f_max_hz``, and *records* the full report -- including any "rigid walls
within the transition distance are underresolved" warning -- in
``mesh_meta.json["cad"]["frequency_validation"]``. A mesh whose source-adjacent
walls the validator calls under-resolved is written with that warning on the record
instead of being silently blessed.

Determinism
-----------
Same recipe + same ``MeshSpec`` -> the same mesh bytes. gmsh's 2D mesher is
deterministic for a fixed geometry and size field, and the recipe fully determines
the STEP geometry. The STEP *file* sha256 is NOT a recipe key: OCC stamps
``FILE_NAME`` with the write time, so two builds of the same recipe differ in those
bytes while their geometry is identical. The mesh cache key (``design.hash()`` +
``mesh.hash()``, ``build.mesh_cache_key``'s base) is what identifies a mesh; this
module records it but keeps NO cross-run mesh cache (like ``grid_build.py``, and for
the same reason: the CAD tool file is canonical and may change under an old entry).

Units: the CAD tool and the live gmsh model are MILLIMETRES; ``postprocess_mesh`` is
called with ``unit_scale_to_m=1e-3`` and the written ``.msh`` is metres. The bbox
guard (``build._check_bbox``) is what proves the conversion (a 3x3 multicell is
~0.35 m wide, not ~350).
"""
from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import logging
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from ..types import GeometryInvalidError, MeshResult, MeshTooLargeError
from . import sizing, topology
from .build import (SOURCE_TAG, MeshConsistencyError, MeshUnitsError, _check_bbox,
                    _check_dofs, read_msh_summary, res_mm_for_spec)

log = logging.getLogger("hornlab_search.mesh.step_build")

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: The canonical CAD builder, by path (never imported as library code).
CAD_TOOL_RELPATH = "tools/cad/multicell.py"
#: The only tool the ``cad`` block may name (extend here + in the tool together).
CAD_TOOL = "multicell"
#: Exact recipe keys (a key that is not here is refused, never passed through).
CAD_KEYS = (
    "tool", "n_h", "n_v", "alpha_total_deg", "beta_total_deg", "length_mm", "z_s_mm",
    "r_throat_mm", "septum_mm", "throat_wall_mm", "flare_hz",
)
#: Mirror of ``tools/cad/multicell.MIN_SEPTUM_MM`` (the closed-surface solver contract).
MIN_SEPTUM_MM = 1.5
#: Cell counts the WP14 recipe may ask for (the tool itself accepts >= 1).
CELL_RANGE = (2, 8)

DRIVER_LABEL = "driver"
WALL_LABEL = "wall"
DRIVER_TAG = int(SOURCE_TAG)          # 2 == SD1D1001 (hornlab_mesher.tags.PhysicalGroup)
WALL_TAG = 1                          # 1 == SD1G0
LABELS = (DRIVER_LABEL, WALL_LABEL)

#: Source adjacency distance for the fine size region. Matches the default
#: ``transition_mm`` of ``mesh_validation.mesh_frequency_validation`` so the region
#: that is refined is exactly the region the "source wall" check measures.
SOURCE_TRANSITION_MM = 200.0

#: Face-order/vertex-match tolerance the mesher uses, in mm (model units).
POSTPROCESS_TOLERANCE_MM = 1.0e-3

STEP_FILENAME = "multicell.step"


class CadParamsError(ValueError):
    """A ``cad`` recipe block the adapter refuses (shape/type/range)."""


# ------------------------------------------------------------------ recipe


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _isint(v) -> bool:
    return (not isinstance(v, bool)) and isinstance(v, (int, float)) and float(v) == int(v)


def validate_cad_params(block) -> None:
    """Validate a ``design.params["cad"]`` recipe. Raises :class:`CadParamsError`.

    Exact keys, strict types, and the tool's own hard schema limits (septum >= 1.5 mm,
    cells 2..8, angles in (0, 180), 0 < z_s < length). Derived-geometry refusals the
    tool encodes (throat clearance, septum-plane gap) are re-checked at build time by
    the tool itself, not duplicated here.
    """
    if not isinstance(block, dict):
        raise CadParamsError(f"cad params must be a mapping, got {type(block).__name__}")
    unknown = sorted(set(block) - set(CAD_KEYS))
    if unknown:
        raise CadParamsError(f"cad: unknown key(s) {unknown} (legal: {list(CAD_KEYS)})")
    missing = [k for k in CAD_KEYS if k not in block]
    if missing:
        raise CadParamsError(
            f"cad: missing required key(s) {missing}; the recipe is the single source of "
            "truth and carries every key (no hidden tool defaults)")
    if not isinstance(block["tool"], str) or block["tool"] != CAD_TOOL:
        raise CadParamsError(
            f"cad.tool must be {CAD_TOOL!r}, got {block['tool']!r}")
    lo, hi = CELL_RANGE
    for key in ("n_h", "n_v"):
        value = block[key]
        if not _isint(value):
            raise CadParamsError(f"cad.{key} must be an integer, got {value!r}")
        if not lo <= int(value) <= hi:
            raise CadParamsError(
                f"cad.{key} must be in [{lo}, {hi}], got {value!r}")
    for key, (low, high) in (
        ("alpha_total_deg", (0.0, 180.0)),
        ("beta_total_deg", (0.0, 180.0)),
    ):
        value = block[key]
        if not _isnum(value) or not low < float(value) < high:
            raise CadParamsError(
                f"cad.{key} must be a finite number in ({low:g}, {high:g}), got {value!r}")
    for key in ("length_mm", "r_throat_mm", "throat_wall_mm"):
        value = block[key]
        if not _isnum(value) or not float(value) > 0.0:
            raise CadParamsError(f"cad.{key} must be a finite number > 0, got {value!r}")
    if not _isnum(block["z_s_mm"]) or not 0.0 < float(block["z_s_mm"]) < float(block["length_mm"]):
        raise CadParamsError(
            "cad.z_s_mm must satisfy 0 < z_s < length_mm, got "
            f"z_s={block['z_s_mm']!r}, length={block['length_mm']!r}")
    if not _isnum(block["septum_mm"]) or float(block["septum_mm"]) < MIN_SEPTUM_MM:
        raise CadParamsError(
            f"cad.septum_mm={block['septum_mm']!r} mm is below the closed-surface solver "
            f"minimum {MIN_SEPTUM_MM} mm")
    if not _isnum(block["flare_hz"]) or float(block["flare_hz"]) < 0.0:
        raise CadParamsError(
            f"cad.flare_hz must be a finite number >= 0 (0 = straight), "
            f"got {block['flare_hz']!r}")


# ------------------------------------------------------------------ the CAD tool


@functools.lru_cache(maxsize=4)
def load_cad_tool(path: Path | None = None):
    """Load ``tools/cad/multicell.py`` by file path (it is not library code).

    The tool stays the canonical builder; nothing here re-implements its geometry.
    Cached per resolved path: the module body is definitions only (build123d is
    imported lazily inside the tool), so re-executing it per candidate would be
    wasted work, not stale state.
    """
    tool_path = Path(path) if path is not None else _REPO_ROOT / CAD_TOOL_RELPATH
    tool_path = tool_path.resolve()
    if not tool_path.is_file():
        raise FileNotFoundError(
            f"the CAD tool {tool_path} is missing; the cad route builds its STEP with "
            f"{CAD_TOOL_RELPATH} (repo root {_REPO_ROOT}) and refuses to guess a builder")
    name = "hornlab_search_cad_multicell"
    spec = importlib.util.spec_from_file_location(name, tool_path)
    if spec is None or spec.loader is None:                 # pragma: no cover - defensive
        raise ImportError(f"could not load the CAD tool from {tool_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _tool_params(tool, recipe: dict):
    """``cad`` block -> the tool's own ``MulticellParams`` (mm / deg)."""
    values = {k: v for k, v in recipe.items() if k != "tool"}
    values["n_h"] = int(values["n_h"])
    values["n_v"] = int(values["n_v"])
    params = replace(tool.DEFAULTS, **values)
    params.validate()                                       # the tool's own refusals
    return params


def build_cad_step(recipe: dict, out_step: Path) -> dict:
    """Build the solid, write the labelled STEP and round-trip its labels.

    Returns the tool's own result dict (``params``, ``derived``, ``solid``,
    ``inventory``, ``path``) plus ``tool_path``. The tool deletes a STEP whose
    labels do not round-trip, so a returned path always satisfies the contract.
    """
    validate_cad_params(recipe)
    tool = load_cad_tool()
    out_step = Path(out_step)
    out_step.parent.mkdir(parents=True, exist_ok=True)
    params = _tool_params(tool, recipe)
    try:
        result = tool.export(out_step, params)              # build + check + write + round trip
    except (ValueError, RuntimeError) as exc:
        raise GeometryInvalidError(f"cad: {exc}") from exc
    inventory = dict(result["inventory"])
    if set(inventory) - set(LABELS):
        raise GeometryInvalidError(
            f"cad: STEP carries unexpected face labels {sorted(inventory)}; "
            f"the adapter knows {list(LABELS)}")
    if inventory.get(DRIVER_LABEL, 0) != 1:
        raise GeometryInvalidError(
            f"cad: STEP must carry exactly one {DRIVER_LABEL!r} face, got "
            f"{inventory.get(DRIVER_LABEL, 0)}")
    result["tool_path"] = str(Path(tool.__file__).resolve())
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ------------------------------------------------------------------ gmsh session


def _import_and_mark(step_path: Path, raw_path: Path, res_mm: dict) -> dict:
    """OCC-import the STEP, map labels to surfaces, tag them, mesh to ``raw_path`` (mm).

    Runs inside the mesher's own ``_GMSH_LOCK`` and opens/finalizes its own gmsh
    session. A session that was already open is cleared like ``hornlab_mesher``'s own
    build does (its model is replaced) but its options are left alone. Every surface
    must be in exactly one physical group before meshing (``step_prepare``'s contract).
    """
    import gmsh
    from hornlab_mesher.builders._occ import add_physical_groups
    from hornlab_mesher.mesher import _GMSH_LOCK
    from hornlab_mesher.native_env import preserve_native_windows_path
    from hornlab_mesher.step_mapping import advanced_face_order_for_surfaces
    from hornlab_mesher.step_text import parse_styled_face_groups

    step_path, raw_path = Path(step_path), Path(raw_path)
    h_fine = float(res_mm["throat"])
    h_coarse = float(res_mm["mouth"])

    with _GMSH_LOCK:
        initialized_here = False
        try:
            if not gmsh.isInitialized():
                with preserve_native_windows_path():
                    gmsh.initialize(interruptible=False)
                    initialized_here = True
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.clear()
            gmsh.model.add("HornLabCadStep")
            gmsh.model.occ.importShapes(str(step_path), highestDimOnly=True)
            gmsh.model.occ.synchronize()

            volumes = [int(tag) for dim, tag in gmsh.model.getEntities(3)]
            if len(volumes) != 1:
                raise GeometryInvalidError(
                    f"cad: the STEP imports as {len(volumes)} volume(s); the BEM surface "
                    "contract needs exactly one closed solid (the CAD tool guarantees it)")
            surfaces = [int(tag) for _dim, tag in sorted(gmsh.model.getEntities(2))]
            if not surfaces:
                raise GeometryInvalidError("cad: the imported STEP has no surfaces")
            try:
                face_order = advanced_face_order_for_surfaces(step_path, surfaces)
                styled = parse_styled_face_groups(step_path)
            except Exception as exc:                        # StepFaceOrderError / parse error
                raise GeometryInvalidError(
                    f"cad: cannot map the STEP face labels onto the imported surfaces: {exc}"
                ) from exc

            label_of_face: dict[int, str] = {}
            for label, face_ids in styled.items():
                for face_id in face_ids:
                    label_of_face[int(face_id)] = str(label)
            per_surface = [label_of_face.get(int(face)) for face in face_order]
            unlabelled = [tag for tag, label in zip(surfaces, per_surface) if label is None]
            if unlabelled:
                raise GeometryInvalidError(
                    f"cad: {len(unlabelled)} of {len(surfaces)} imported surface(s) carry no "
                    f"STEP label (first: {unlabelled[:8]}); every surface must be grouped")
            bad = sorted({label for label in per_surface
                          if label is not None and label not in LABELS})
            if bad:
                raise GeometryInvalidError(
                    f"cad: STEP carries unexpected face label(s) {bad}; the adapter knows "
                    f"{list(LABELS)} (driver -> tag {DRIVER_TAG}, wall -> tag {WALL_TAG})")

            groups: dict[int, list[int]] = {}
            for tag, label in zip(surfaces, per_surface):
                groups.setdefault(DRIVER_TAG if label == DRIVER_LABEL else WALL_TAG, []).append(tag)
            driver_surfaces = groups.get(DRIVER_TAG, [])
            if len(driver_surfaces) != 1:
                raise GeometryInvalidError(
                    f"cad: exactly one surface must carry the {DRIVER_LABEL!r} label, got "
                    f"{len(driver_surfaces)}")
            add_physical_groups(groups)

            # Uniform fine region around the driven face, the recipe's mouth resolution
            # elsewhere (the mesher's throat = mouth / 2 convention).
            field = gmsh.model.mesh.field
            distance = field.add("Distance")
            field.setNumbers(distance, "SurfacesList", [int(t) for t in driver_surfaces])
            field.setNumber(distance, "Sampling", 100)
            threshold = field.add("Threshold")
            field.setNumber(threshold, "InField", distance)
            field.setNumber(threshold, "SizeMin", h_fine)
            field.setNumber(threshold, "SizeMax", h_coarse)
            field.setNumber(threshold, "DistMin", 0.0)
            field.setNumber(threshold, "DistMax", float(SOURCE_TRANSITION_MM))
            background = field.add("Min")
            field.setNumbers(background, "FieldsList", [threshold])
            field.setAsBackgroundMesh(background)
            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
            # MeshAdapt: measured most uniform on these OCC lofts/septa (max edge
            # 1.38x target) where Frontal-Delaunay left 4x outliers at pinch corners.
            gmsh.option.setNumber("Mesh.Algorithm", 1)
            gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
            gmsh.option.setNumber("Mesh.Binary", 0)
            gmsh.model.mesh.generate(2)
            gmsh.write(str(raw_path))
        except GeometryInvalidError:
            raise
        except Exception as exc:                            # gmsh raises bare Exception
            raise GeometryInvalidError(
                f"cad: gmsh could not mesh the imported STEP: {exc}") from exc
        finally:
            if initialized_here and gmsh.isInitialized():
                with preserve_native_windows_path():
                    gmsh.finalize()

    return {
        "gmsh_surfaces": len(surfaces),
        "driver_surfaces": len(driver_surfaces),
        "wall_surfaces": len(groups.get(WALL_TAG, [])),
    }


# ------------------------------------------------------------------ postprocess


def _triangle_arrays(mesh):
    """(points, triangles, physical tags) from a meshio mesh, triangle block only."""
    index = [i for i, block in enumerate(mesh.cells) if block.type in ("triangle", "triangle3")]
    if not index:
        raise GeometryInvalidError("cad: the gmsh output has no triangle block")
    block = mesh.cells[index[0]].data
    tags = mesh.cell_data["gmsh:physical"][index[0]]
    return np.asarray(mesh.points, dtype=float), np.asarray(block, dtype=np.int64), \
        np.asarray(tags, dtype=np.int64)


def postprocess_cad_raw(raw_path: Path, res_mm: dict):
    """``postprocess_mesh`` + the driver-face spec, in millimetres."""
    import meshio
    from hornlab_mesher.mesh_repair import postprocess_mesh
    from hornlab_mesher.step_mapping import StepFaceGroup, StepLabelSelector
    from hornlab_mesher.step_prepare import OccSurfaceRole

    source_specs = [StepFaceGroup(
        DRIVER_LABEL,
        StepLabelSelector(DRIVER_LABEL),
        OccSurfaceRole("source"),
        tag=DRIVER_TAG,
        resolution_mm=float(res_mm["throat"]),
    )]
    raw = meshio.read(Path(raw_path))
    repaired, repair, topo = postprocess_mesh(
        raw, source_specs,
        symmetry_planes=(),
        tolerance=POSTPROCESS_TOLERANCE_MM,
        unit_scale_to_m=1e-3,
    )
    return repaired, repair, topo, source_specs


def write_mesh_metres(path: Path, points_mm: np.ndarray, triangles: np.ndarray,
                      tags: np.ndarray) -> Path:
    """Write a gmsh 2.2 ASCII ``.msh`` in METRES with the physical-group names."""
    import meshio
    from hornlab_mesher.tags import PHYSICAL_NAMES

    used = sorted({int(tag) for tag in np.asarray(tags).tolist()})
    names = {tag: PHYSICAL_NAMES[tag] for tag in used if tag in PHYSICAL_NAMES}
    mesh = meshio.Mesh(
        points=np.asarray(points_mm, dtype=float) * 1e-3,
        cells=[("triangle", np.asarray(triangles, dtype=np.int64))],
        cell_data={
            "gmsh:physical": [np.asarray(tags, dtype=np.int32)],
            "gmsh:geometrical": [np.asarray(tags, dtype=np.int32)],
        },
        field_data={name: np.array([tag, 2], dtype=np.int32) for tag, name in names.items()},
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meshio.write(path, mesh, file_format="gmsh22", binary=False)
    return path


# ------------------------------------------------------------------ provenance


def _jsonable(value):
    """Recursively convert numpy/path values so ``json.dumps`` cannot fail."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def _meta_path(out_dir: Path) -> Path:
    return Path(out_dir) / "mesh_meta.json"


# ------------------------------------------------------------------ build


def build_mesh_from_cad(recipe: dict, mesh, cfg, out_dir: Path, *,
                        mode: str | None = None, design_hash: str | None = None) -> MeshResult:
    """``cad`` recipe + ``MeshSpec`` -> ``<out_dir>/mesh.msh`` (metres) + provenance.

    Pipeline, in order (each step is the pinned library's, not ours):

    1. ``tools/cad/multicell.py`` builds the solid and writes the labelled STEP to
       ``<out_dir>/cad/multicell.step`` (round-trip labels checked by the tool);
    2. gmsh OCC import + geometry-matched face mapping -> physical groups
       (driver -> tag 2 / SD1D1001, wall -> tag 1 / SD1G0, every surface grouped);
    3. ``Mesh.generate(2)`` -> meshio -> ``postprocess_mesh(unit_scale_to_m=1e-3)``;
    4. ``mesh_frequency_validation`` at ``mesh.f_max_hz`` (the driven patch must
       resolve it; other warnings are recorded);
    5. write the ``.msh`` in metres, then the SAME guards as ``build.py``:
       bbox in [0.02, 5.0] m, source tag 2 non-empty, dof cap,
       ``topology.check_surface``.

    ``cfg`` is the run ``Config`` (dof caps / ``dof_per_triangle``/``rear_res_factor``
    come from ``cfg.mesh``); ``design_hash`` is echoed into the provenance key.

    WP12: a run whose brief carries ``mounting`` (a rear enclosure) is REFUSED here with a clean
    ``GeometryInvalidError``: CAD + enclosure is explicitly out of this pass (the labelled-STEP
    solid is authored by ``tools/cad/multicell.py``, which has no enclosure builder). The refusal
    runs before any mesher import, so it is honest even where the mesher is absent.
    """
    mounting = getattr(cfg, "mounting", None)
    if mounting is not None:
        raise GeometryInvalidError(
            "CAD + enclosure is not implemented in this pass: a cad design is meshed from the "
            "labelled STEP authored by tools/cad/multicell.py (mesh/step_build.py), and that "
            "tool has no enclosure builder. Drop the brief's mounting block for this design or "
            "use a formula/GRID design for an enclosure candidate.")

    import hornlab_mesher  # noqa: F401  (pin guard: a missing mesher fails clearly here)
    from hornlab_mesher.mesh_validation import mesh_frequency_validation

    t0 = time.perf_counter()
    validate_cad_params(recipe)
    if not isinstance(mesh.quadrants, str) or mesh.quadrants != "1234":
        raise GeometryInvalidError(
            "cad: the multicell STEP is a FULL solid (mirror-symmetric but not reduced), "
            f"so mesh.quadrants must be '1234'; got {mesh.quadrants!r}. A reduced solve of a "
            "full model would double-count the domain.")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    step_path = out_dir / "cad" / STEP_FILENAME
    built = build_cad_step(recipe, step_path)
    step_sha = _sha256(step_path)
    inventory = dict(built["inventory"])

    res = res_mm_for_spec(mesh, cfg)
    res = {"throat": float(res["throat"]), "mouth": float(res["mouth"]),
           "rear": float(res["rear"])}
    raw_path = out_dir / "cad" / "multicell_raw_mm.msh"
    try:
        mapped = _import_and_mark(step_path, raw_path, res)
        repaired, repair, topo_report, source_specs = postprocess_cad_raw(raw_path, res)
        points_mm, triangles, tags = _triangle_arrays(repaired)

        freq = mesh_frequency_validation(
            points_mm, triangles, tags, source_specs,
            unit_scale_to_m=1e-3,
            requested_max_frequency_hz=float(mesh.f_max_hz),
        )
        patch = freq["per_source"].get(DRIVER_LABEL, {})
        patch_limit = float(patch.get("max_valid_frequency_hz", 0.0))
        if patch_limit < float(mesh.f_max_hz):
            raise GeometryInvalidError(
                f"cad: the driver patch resolves {patch_limit:.0f} Hz but the recipe asks for "
                f"{float(mesh.f_max_hz):.0f} Hz ({patch.get('triangle_count', 0)} triangle(s), "
                f"requested {patch.get('requested_resolution_mm', 0.0):.2f} mm); lower "
                "mesh.f_max_hz or epw")
        if freq.get("status") != "valid":
            log.warning(
                "cad mesh: %s; the mesh is written with the frequency report on its record",
                "; ".join(freq.get("warnings") or ["status invalid"]))

        out_path = out_dir / "mesh.msh"
        write_mesh_metres(out_path, points_mm, triangles, tags)

        summary, xyz, xyz_tri = read_msh_summary(out_path, return_arrays=True)
        want = sizing.SYMMETRY_PLANE[mesh.quadrants]
        try:
            _check_bbox(summary["bbox_m"])
            if summary["tags"].get(SOURCE_TAG, 0) <= 0:
                raise GeometryInvalidError(
                    f"cad: mesh has no elements on physical tag {SOURCE_TAG} (SD1D1001, the "
                    f"source); tags present: {summary['tags']}")
            _check_dofs(summary["n_triangles"], summary["n_nodes_used"], mesh, cfg, mode)
            topology.check_surface(xyz, xyz_tri, want)
        except (MeshConsistencyError, MeshUnitsError, GeometryInvalidError, MeshTooLargeError):
            out_path.unlink(missing_ok=True)     # never leave an unusable mesh behind
            raise

        result = MeshResult(
            path=str(out_path), n_triangles=summary["n_triangles"], n_dof=None,
            quadrants=mesh.quadrants, symmetry_plane=want,
            res_mm=dict(res), bbox_m=tuple(summary["bbox_m"]),
            seconds=time.perf_counter() - t0)

        key = (f"{design_hash}-{mesh.hash()}" if design_hash
               else f"cad-{mesh.hash()}")
        provenance = _jsonable({
            "key": key,
            "result": {
                "path": result.path, "n_triangles": result.n_triangles,
                "n_dof": result.n_dof, "quadrants": result.quadrants,
                "symmetry_plane": result.symmetry_plane, "res_mm": dict(res),
                "bbox_m": list(result.bbox_m), "seconds": result.seconds,
            },
            "summary": summary,
            "cad": {
                "tool": CAD_TOOL_RELPATH,
                "tool_path": built["tool_path"],
                "tool_sha256": _sha256(Path(built["tool_path"])),
                "recipe": dict(recipe),
                "derived": built["derived"],
                "solid": {k: v for k, v in built["solid"].items()},
                "step_path": str(step_path),
                "step_sha256": step_sha,
                "step_bytes": int(step_path.stat().st_size),
                "face_inventory": inventory,
                "gmsh_surfaces": int(mapped["gmsh_surfaces"]),
                "driver_surfaces": int(mapped["driver_surfaces"]),
                "wall_surfaces": int(mapped["wall_surfaces"]),
                "physical_tags": {str(WALL_TAG): "SD1G0", str(DRIVER_TAG): "SD1D1001"},
                "frequency_validation": freq,
                "repair": repair,
                "topology": topo_report,
            },
        })
        _meta_path(out_dir).write_text(
            json.dumps(provenance, indent=1, sort_keys=True), encoding="utf-8")
    finally:
        raw_path.unlink(missing_ok=True)

    log.info("cad mesh %s: %d triangles, %d vertices, %.2f s",
             key, result.n_triangles, summary["n_nodes_used"], result.seconds)
    return result
