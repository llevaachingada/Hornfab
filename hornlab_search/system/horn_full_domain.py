"""Full-domain closure of a saved horn asset for Boundary Lab assembled solves.

Why this module exists
----------------------
The saved assets used by the woofer-system feature are **quarter models**: their
``mesh.msh`` is a fundamental-domain patch whose free edges all lie on the ``x=0`` /
``y=0`` symmetry planes (``boundarylab.assemble.horn_mesh_qa`` classifies them as
``symmetric_patch``).  A separate-mesh Boundary Lab assembly needs a *closed*
full-domain horn surface.  This module rebuilds the SAME saved design through the
EXISTING mesher route (:func:`hornlab_search.mesh.build.build_mesh`) with
``MeshSpec.quadrants="1234"``; it never mirrors, welds or writes geometry itself.

Route selection (read from ``design.json``, exactly as ``mesh/build.py`` does):

* ``params["grid"]`` with a ``rows`` recipe -> the point-grid adapter
  (:mod:`hornlab_search.mesh.grid_build`).  The saved recipe is a quarter
  (``span: quarter``); the full ring is the generator's own ``span: full`` mode, which
  requires ``n_phi >= grid.MIN_PHI_FULL``.  Only the azimuthal *sampling* changes:
  profile knobs, ``n_s``, wall thickness and every geometry parameter are untouched.
* any formula family -> ``build_mesh`` renders the same design at ``quadrants="1234"``
  directly (``SYMMETRY_PLANE["1234"] is None``).

Provenance gate (handoff REF-02)
--------------------------------
Before the full build the module rebuilds the asset's ORIGINAL quarter mesh
(``quadrants="1"``) from ``design.json`` at the run's own ``epw`` / ``f_max`` / dof cap
and compares its bounding box and wall area with the stored ``mesh.msh``.  A changed
macroscopic horn is a hard ``ProvenanceError``; a different triangulation is not.

Outputs (under ``system_runs/system/ref_case/horn_full/<case_tag>/``)
---------------------------------------------------------------------
* ``mesh.msh``          -- the full-domain mesh, metres, written by gmsh
* ``full_mesh_qa.json`` -- ``horn_mesh_qa`` verdict + tag counts
* ``provenance.json``   -- design hashes, source run, lib pins, original-vs-full parity

Units: the mesher writes METRES (``build_mesh`` enforces 0.02-5 m).  This module adds the
Boundary Lab 0.1-10 m scale guard on the full mesh as requested by the reference-case
handoff.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata as importlib_metadata
import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from ..config import Config, load_config, mesh_spec
from ..design.generators import grid as grid_gen
from ..mesh import sizing
from ..mesh.build import build_mesh, read_msh_summary
from ..system.boundarylab import assemble
from ..types import Design, MeshSpec

__all__ = [
    "DEFAULT_RUNS_ROOT",
    "DEFAULT_RUN_NAME",
    "DEFAULT_DESIGN_HASH",
    "DEFAULT_CASE_TAG",
    "PROVENANCE_SCHEMA",
    "QA_SCHEMA",
    "HornAssetRef",
    "ProvenanceGate",
    "FullDomainMeshReport",
    "HornFullDomainError",
    "ProvenanceError",
    "FullDomainQAError",
    "default_out_root",
    "discover_asset",
    "build_full_domain_mesh",
    "full_grid_params",
    "mirrored_bbox_deltas",
    "validate_full_domain_qa",
]

#: Canonical read-only run tree (the same default ``horn_assets`` uses).
DEFAULT_RUNS_ROOT = Path("C:/Users/hunte/Hrns/hornlab-search/runs")
#: Primary reference asset (handoff W1 route A / REF-02).
DEFAULT_RUN_NAME = "20261118T200653Z-screen-31495a"
DEFAULT_DESIGN_HASH = "9e02db06ecc3"
DEFAULT_CASE_TAG = "lecleach_rollback_1in_v6_9e02db06ecc3"

PROVENANCE_SCHEMA = "hornlab.system.horn_full_domain.provenance.v1"
QA_SCHEMA = "hornlab.system.horn_full_domain.qa.v1"

#: Stated parity tolerance for the provenance gate (metres).  The same mesher + pins
#: reproduce the saved quarter mesh bit-for-bit here; 1 um still tolerates a different
#: triangulation without hiding a changed horn.
BBOX_PARITY_TOL_M = 1e-6
#: Relative wall-area tolerance for the provenance gate.
AREA_PARITY_REL = 1e-4
#: Boundary Lab scale guard on the full mesh, metres (handoff step 5).
FULL_BBOX_MIN_M = 0.1
FULL_BBOX_MAX_M = 10.0
#: Mirror parity tolerance for the full-vs-quarter bbox check (metres).
MIRROR_TOL_M = 1e-6

#: Source physical tag (SD1D1001) -- reproduced from ``mesh.build`` (contract section 3).
SOURCE_TAG = 2


class HornFullDomainError(RuntimeError):
    """Base class for a refused full-domain rebuild."""


class ProvenanceError(HornFullDomainError):
    """The saved design does not reproducibly regenerate its stored quarter mesh."""


class FullDomainQAError(HornFullDomainError):
    """The rebuilt full mesh is not a closed, mirrored, metre-scale horn surface."""


# --------------------------------------------------------------------------- asset ref


@dataclass(frozen=True)
class HornAssetRef:
    """Read-only provenance of one saved design directory."""

    runs_root: Path
    run_name: str
    run_dir: Path
    design_dir: Path
    design_hash: str
    family: str
    brief: str | None
    config_path: Path
    design_path: Path
    status_path: Path
    mesh_path: Path
    run_json_path: Path
    design: Design


def discover_asset(runs_root: str | Path | None = None,
                   run_name: str = DEFAULT_RUN_NAME,
                   design_hash: str = DEFAULT_DESIGN_HASH) -> HornAssetRef:
    """Locate and load one saved design from the canonical (read-only) run tree.

    Raises :class:`FileNotFoundError` when the run/design directory or its
    ``design.json`` / ``config.yaml`` / ``mesh.msh`` is absent -- never fabricates a
    recipe from memory.  The reconstructed :class:`~hornlab_search.types.Design`
    hash is verified against ``design.json["design_hash"]``.
    """
    root = Path(runs_root) if runs_root is not None else DEFAULT_RUNS_ROOT
    run_dir = root / run_name
    design_dir = run_dir / "designs" / design_hash
    design_path = design_dir / "design.json"
    if not design_path.is_file():
        raise FileNotFoundError(f"saved design.json not found: {design_path}")
    config_path = run_dir / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"run config.yaml not found: {config_path}")
    meta = json.loads(design_path.read_text(encoding="utf-8"))
    family = str(meta.get("family") or "")
    params = meta.get("params")
    if not family or not isinstance(params, dict):
        raise FileNotFoundError(f"design.json lacks family/params: {design_path}")
    design = Design(family=family, params=params)  # type: ignore[arg-type]
    recorded = meta.get("design_hash")
    if recorded and design.hash() != recorded:
        raise ProvenanceError(
            f"design.json recipe does not hash to its recorded design_hash: "
            f"reconstructed {design.hash()} != recorded {recorded}")
    generator = meta.get("generator") if isinstance(meta.get("generator"), dict) else {}
    brief = generator.get("brief") if isinstance(generator.get("brief"), str) else None
    return HornAssetRef(
        runs_root=root,
        run_name=run_name,
        run_dir=run_dir,
        design_dir=design_dir,
        design_hash=design.hash(),
        family=family,
        brief=brief,
        config_path=config_path,
        design_path=design_path,
        status_path=design_dir / "status.json",
        mesh_path=design_dir / "mesh.msh",
        run_json_path=run_dir / "run.json",
        design=design,
    )


# --------------------------------------------------------------------------- lib pins


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _installed_mesher_commit() -> str | None:
    """The installed ``hornlab-waveguide-mesher`` VCS commit, or ``None`` if unknown."""
    try:
        dist = importlib_metadata.distribution("hornlab-waveguide-mesher")
        raw = dist.read_text("direct_url.json")
        if raw:
            info = json.loads(raw)
            commit = (info.get("vcs_info") or {}).get("commit_id")
            if isinstance(commit, str) and commit:
                return commit
    except Exception:  # noqa: BLE001 - provenance is recorded, never guessed
        return None
    return None


def _installed_gmsh_version() -> str | None:
    try:
        import gmsh  # type: ignore[import-not-found]
        return str(getattr(gmsh, "__version__", "") or "") or None
    except Exception:  # noqa: BLE001
        return None


def _lib_pins(ref: HornAssetRef) -> dict[str, Any]:
    run_json = _read_json(ref.run_json_path) or {}
    raw_pins = run_json.get("lib_shas")
    pins: dict[str, Any] = raw_pins if isinstance(raw_pins, dict) else {}
    installed_mesher = _installed_mesher_commit()
    return {
        "run_lib_shas": {str(k): str(v) for k, v in sorted(pins.items())},
        "installed_mesher_commit": installed_mesher,
        "installed_gmsh_version": _installed_gmsh_version(),
        "run_config_sha": run_json.get("config_sha"),
        "run_config_name": run_json.get("config_name"),
    }


def _verify_mesher_pin(ref: HornAssetRef, pins: dict[str, Any]) -> None:
    pinned = pins["run_lib_shas"].get("hornlab_mesher")
    installed = pins["installed_mesher_commit"]
    if pinned and installed and pinned != installed:
        raise ProvenanceError(
            "mesher pin mismatch: the run was meshed with hornlab_mesher "
            f"{pinned}, but the installed hornlab-waveguide-mesher is {installed}; "
            "a full-domain rebuild under different pins is not the same recipe")


# --------------------------------------------------------------------------- full recipe


def full_grid_params(params: dict[str, Any], *,
                     min_phi_full: int | None = None) -> dict[str, Any]:
    """Return a deep copy of a saved grid recipe promoted to the generator's full ring.

    Only the model extent changes: ``span: full`` plus the azimuthal sample count raised
    to the generator's minimum for an honest full circle.  The count is rounded up to a
    multiple of 8 so ``0``, ``45``, ``90``, ``180`` and ``270`` deg rows exist, keeping
    the full bbox an exact mirror of the quarter's extents.  Profile knobs, ``n_s``,
    ``rows`` kind and ``wall_thickness_mm`` are byte-identical to the saved recipe.

    Raises :class:`HornFullDomainError` for a non-rows grid recipe, whose full-ring
    sampling law this lane does not own.
    """
    block = params.get("grid")
    if not isinstance(block, dict):
        raise HornFullDomainError(
            "not a grid design; the formula route needs no recipe edit")
    if "rows" not in block:
        raise HornFullDomainError(
            "grid design without a rows recipe: full-ring sampling is only defined for "
            "the rows generator in this lane")
    out = copy.deepcopy(params)
    full = out["grid"]
    floor = int(min_phi_full if min_phi_full is not None else grid_gen.MIN_PHI_FULL)
    original = int(full.get("n_phi", floor))
    # Multiple of 8 -> exact 45 deg diagonal + cardinal rows, so |x|/|y| parity is exact.
    n_phi = max(floor, original)
    n_phi = 8 * int(math.ceil(n_phi / 8))
    full["span"] = "full"
    full["n_phi"] = n_phi
    return out


# --------------------------------------------------------------------------- bbox parity


def mirrored_bbox_deltas(quarter_bbox: tuple[float, ...],
                         full_bbox: tuple[float, ...]) -> dict[str, float]:
    """Absolute deltas between the full bbox and the quarter bbox mirrored about x/y.

    ``bbox = (xmin, ymin, zmin, xmax, ymax, zmax)`` in metres.  The expected full bbox is
    ``(-xmax_q, -ymax_q, zmin_q, xmax_q, ymax_q, zmax_q)``; ``z`` (throat -> mouth) must
    be unchanged.  Returns each delta plus ``max``.
    """
    if len(quarter_bbox) != 6 or len(full_bbox) != 6:
        raise ValueError("bbox must have 6 values (xmin,ymin,zmin,xmax,ymax,zmax)")
    qx0, qy0, qz0, qx1, qy1, qz1 = (float(v) for v in quarter_bbox)
    fx0, fy0, fz0, fx1, fy1, fz1 = (float(v) for v in full_bbox)
    deltas = {
        "x_minus": abs(fx0 - (-qx1)),
        "y_minus": abs(fy0 - (-qy1)),
        "x_plus": abs(fx1 - qx1),
        "y_plus": abs(fy1 - qy1),
        "z_min": abs(fz0 - qz0),
        "z_max": abs(fz1 - qz1),
    }
    deltas["max"] = max(deltas.values())
    return deltas


def validate_full_domain_qa(qa: Any, quarter_bbox: tuple[float, ...], *,
                            tol_m: float = MIRROR_TOL_M) -> None:
    """Raise :class:`FullDomainQAError` unless ``qa`` is a closed, mirrored full horn.

    ``qa`` is a :class:`hornlab_search.system.boundarylab.assemble.MeshQA`.
    """
    problems: list[str] = []
    if not qa.closed:
        problems.append(f"not closed ({qa.free_edges} free edges)")
    if not qa.orientation_consistent:
        problems.append("triangle orientation is inconsistent")
    if qa.free_edges != 0:
        problems.append(f"expected 0 free edges, got {qa.free_edges}")
    if qa.full_open_holes != 0:
        problems.append(f"expected 0 open holes, got {qa.full_open_holes}")
    if qa.duplicate_points != 0:
        problems.append(f"expected 0 duplicate points, got {qa.duplicate_points}")
    if qa.symmetric_patch:
        problems.append("mesh is still a symmetry patch, not a full domain")
    if not qa.groups:
        problems.append("no physical groups in the full mesh")
    full_bbox = (*qa.bbox_min_m, *qa.bbox_max_m)
    extent = max(full_bbox[3] - full_bbox[0], full_bbox[4] - full_bbox[1],
                 full_bbox[5] - full_bbox[2])
    if not FULL_BBOX_MIN_M <= extent <= FULL_BBOX_MAX_M:
        problems.append(
            f"bbox largest extent {extent:.6g} m outside the Boundary Lab "
            f"[{FULL_BBOX_MIN_M}, {FULL_BBOX_MAX_M}] m scale guard; bbox={full_bbox}")
    deltas = mirrored_bbox_deltas(quarter_bbox, full_bbox)
    if deltas["max"] > tol_m:
        bad = {k: v for k, v in deltas.items() if k != "max" and v > tol_m}
        problems.append(
            f"full bbox is not the quarter bbox mirrored about x/y within {tol_m:g} m: "
            f"{bad}")
    if problems:
        raise FullDomainQAError("; ".join(problems))


# --------------------------------------------------------------------------- reports


@dataclass(frozen=True)
class ProvenanceGate:
    """Original quarter-mesh regeneration parity (REF-02)."""

    ok: bool
    stored_mesh: Path
    rebuilt_mesh: Path
    stored_bbox_m: tuple[float, ...]
    rebuilt_bbox_m: tuple[float, ...]
    max_abs_bbox_delta_m: float
    stored_area_m2: float
    rebuilt_area_m2: float
    area_rel_delta: float
    stored_triangles: int
    rebuilt_triangles: int
    tol_m: float


@dataclass(frozen=True)
class FullDomainMeshReport:
    """Everything one full-domain rebuild produced (paths, QA and provenance)."""

    case_tag: str
    mesh_path: Path
    qa_json_path: Path
    provenance_json_path: Path
    qa: Any
    provenance_gate: ProvenanceGate
    mesh_summary: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- build


def default_out_root() -> Path:
    """``<checkout>/system_runs/system/ref_case/horn_full``.

    Derived from this file so the default does not depend on the caller's cwd; falls back
    to the cwd when the module is imported from an installed package.
    """
    here = Path(__file__).resolve()
    repo = here.parents[2]
    if (repo / "pyproject.toml").is_file():
        return repo / "system_runs" / "system" / "ref_case" / "horn_full"
    return Path.cwd() / "system_runs" / "system" / "ref_case" / "horn_full"


def _params_sha256(params: dict[str, Any]) -> str:
    blob = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [float(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_full_domain_mesh(
    asset: HornAssetRef | None = None,
    *,
    out_root: str | Path | None = None,
    case_tag: str = DEFAULT_CASE_TAG,
    runs_root: str | Path | None = None,
    run_name: str = DEFAULT_RUN_NAME,
    design_hash: str = DEFAULT_DESIGN_HASH,
    mode: str = "screen",
    epw: float | None = None,
    f_max_hz: float | None = None,
    full_n_phi: int | None = None,
    bbox_tol_m: float = BBOX_PARITY_TOL_M,
    run_provenance_gate: bool = True,
) -> FullDomainMeshReport:
    """Rebuild the saved quarter design as a closed full-domain mesh + QA + provenance.

    Parameters mirror the reference-case handoff: the original design is re-read from
    ``design.json``; ``epw`` / ``f_max_hz`` default to the run's own screen mesh spec (a
    deliberately modest validation density), and the dof cap comes from the run config.

    The provenance gate rebuilds ``quadrants="1"`` first and refuses a changed macroscopic
    horn.  The full build then uses ``quadrants="1234"`` through ``mesh/build.py``; no
    hand mirroring or welding happens here.
    """
    ref = asset if asset is not None else discover_asset(runs_root, run_name, design_hash)
    cfg: Config = load_config(ref.config_path)
    if not ref.mesh_path.is_file():
        raise FileNotFoundError(f"stored quarter mesh not found: {ref.mesh_path}")
    stored_summary = cast(dict[str, Any], read_msh_summary(ref.mesh_path))
    stored_bbox = tuple(stored_summary["bbox_m"])

    pins = _lib_pins(ref)
    _verify_mesher_pin(ref, pins)

    orig_spec = mesh_spec(mode, cfg)  # type: ignore[arg-type]
    cap = int(cfg.mesh.dof_cap(mode))
    dpt = float(cfg.mesh.dof_per_triangle)
    slack = float(getattr(cfg.mesh, "max_triangle_slack", 1.15))
    orig_spec = replace(
        orig_spec, quadrants="1",
        max_triangles=sizing.max_triangles_for(cap, "1", dpt, slack))
    full_epw = float(epw if epw is not None else orig_spec.epw)
    full_fmax = float(f_max_hz if f_max_hz is not None else orig_spec.f_max_hz)
    full_spec = MeshSpec(epw=full_epw, f_max_hz=full_fmax, quadrants="1234",
                         max_triangles=sizing.max_triangles_for(cap, "1234", dpt, slack),
                         allow_large_mesh=False,
                         curvature_npts=float(getattr(cfg.mesh, "curvature_npts", 0.0) or 0.0))

    out_dir = Path(out_root) if out_root is not None else default_out_root()
    case_dir = out_dir / case_tag
    case_dir.mkdir(parents=True, exist_ok=True)

    gate = ProvenanceGate(
        ok=False, stored_mesh=ref.mesh_path, rebuilt_mesh=Path(""),
        stored_bbox_m=stored_bbox, rebuilt_bbox_m=(), max_abs_bbox_delta_m=float("nan"),
        stored_area_m2=float(stored_summary["area_m2"]), rebuilt_area_m2=float("nan"),
        area_rel_delta=float("nan"), stored_triangles=int(stored_summary["n_triangles"]),
        rebuilt_triangles=0, tol_m=float(bbox_tol_m))

    if run_provenance_gate:
        gate = _run_provenance_gate(ref, cfg, orig_spec, case_dir / "_provenance_quarter",
                                    stored_summary, tol_m=bbox_tol_m)

    # ---- FULL DOMAIN (the sanctioned route: the existing grid/formula mesher path)
    full_design = _full_design(ref.design, full_n_phi=full_n_phi)
    result = build_mesh(full_design, full_spec, cfg, case_dir, mode=mode)
    mesh_path = Path(result.path)
    summary = cast(dict[str, Any], read_msh_summary(mesh_path))

    # ---- QA via the Boundary Lab classifier
    qa = assemble.horn_mesh_qa(mesh_path)
    validate_full_domain_qa(qa, stored_bbox)
    dups = mirrored_bbox_deltas(stored_bbox, tuple(summary["bbox_m"]))

    qa_payload = {
        "schema": QA_SCHEMA,
        "case_tag": case_tag,
        "design_hash_original": ref.design_hash,
        "design_hash_full": full_design.hash(),
        "qa": qa.to_dict(),
        "mesh_summary": {
            "n_triangles": int(summary["n_triangles"]),
            "n_nodes": int(summary["n_nodes"]),
            "n_nodes_used": int(summary["n_nodes_used"]),
            "bbox_m": [float(v) for v in summary["bbox_m"]],
            "area_m2": float(summary["area_m2"]),
            "tags": {str(k): int(v) for k, v in sorted(summary["tags"].items())},
            "tag_names": {str(k): str(v) for k, v in sorted(summary["tag_names"].items())},
            "source_tag_present": int(summary["tags"].get(SOURCE_TAG, 0)) > 0,
        },
    }
    qa_path = case_dir / "full_mesh_qa.json"
    _write_json(qa_path, qa_payload)

    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "case_tag": case_tag,
        "family": ref.family,
        "brief": ref.brief,
        "design_hash_original": ref.design_hash,
        "design_hash_full": full_design.hash(),
        "full_params_sha256": _params_sha256(full_design.params),
        "source_run": {
            "runs_root": str(ref.runs_root),
            "run_name": ref.run_name,
            "run_dir": str(ref.run_dir),
            "design_dir": str(ref.design_dir),
            "config_path": str(ref.config_path),
            "config_sha": pins["run_config_sha"],
            "config_name": pins["run_config_name"],
        },
        "lib_pins": pins,
        "mesh_spec_original": {
            "epw": float(orig_spec.epw), "f_max_hz": float(orig_spec.f_max_hz),
            "quadrants": orig_spec.quadrants,
            "max_triangles": int(orig_spec.max_triangles),
            "dof_cap": cap, "dof_per_triangle": dpt,
        },
        "mesh_spec_full": {
            "epw": float(full_spec.epw), "f_max_hz": float(full_spec.f_max_hz),
            "quadrants": full_spec.quadrants,
            "max_triangles": int(full_spec.max_triangles),
        },
        "sampling_change": _sampling_change(ref.design.params, full_design.params),
        "provenance_gate": {
            "ok": gate.ok,
            "stored_mesh": str(gate.stored_mesh),
            "rebuilt_mesh": str(gate.rebuilt_mesh),
            "stored_bbox_m": _plain(gate.stored_bbox_m),
            "rebuilt_bbox_m": _plain(gate.rebuilt_bbox_m),
            "max_abs_bbox_delta_m": gate.max_abs_bbox_delta_m,
            "tol_m": gate.tol_m,
            "stored_area_m2": gate.stored_area_m2,
            "rebuilt_area_m2": gate.rebuilt_area_m2,
            "area_rel_delta": gate.area_rel_delta,
            "stored_triangles": gate.stored_triangles,
            "rebuilt_triangles": gate.rebuilt_triangles,
        },
        "full_vs_quarter_bbox": {
            "quarter_bbox_m": _plain(stored_bbox),
            "full_bbox_m": [float(v) for v in summary["bbox_m"]],
            "mirror_deltas_m": dups,
        },
        "full_mesh": {
            "path": str(mesh_path),
            "n_triangles": int(summary["n_triangles"]),
            "n_nodes": int(summary["n_nodes_used"]),
            "physical_groups": list(qa.groups),
            "tag_counts": {str(k): int(v) for k, v in sorted(summary["tags"].items())},
        },
        "units": "metres",
    }
    prov_path = case_dir / "provenance.json"
    _write_json(prov_path, provenance)

    return FullDomainMeshReport(
        case_tag=case_tag,
        mesh_path=mesh_path,
        qa_json_path=qa_path,
        provenance_json_path=prov_path,
        qa=qa,
        provenance_gate=gate,
        mesh_summary={k: summary[k] for k in
                      ("n_triangles", "n_nodes", "n_nodes_used", "bbox_m", "area_m2",
                       "tags", "tag_names")},
        provenance=provenance,
    )


def _full_design(design: Design, *, full_n_phi: int | None = None) -> Design:
    params = design.params
    if isinstance(params, dict) and "grid" in params:
        return Design(family=design.family,
                      params=full_grid_params(params, min_phi_full=full_n_phi))
    # Formula family: build_mesh renders the same recipe at quadrants="1234" directly.
    return design


def _run_provenance_gate(ref: HornAssetRef, cfg: Config, orig_spec: MeshSpec,
                         out_dir: Path, stored_summary: dict[str, Any], *,
                         tol_m: float) -> ProvenanceGate:
    """Rebuild the original quarter mesh and compare it with the stored one."""
    result = build_mesh(ref.design, orig_spec, cfg, out_dir, mode=None)
    rebuilt_path = Path(result.path)
    rebuilt = cast(dict[str, Any], read_msh_summary(rebuilt_path))
    q_bbox = tuple(float(v) for v in stored_summary["bbox_m"])
    r_bbox = tuple(float(v) for v in rebuilt["bbox_m"])
    if len(q_bbox) != 6 or len(r_bbox) != 6:
        raise ProvenanceError("stored/rebuilt bbox is not 6-valued")
    bbox_delta = max(abs(a - b) for a, b in zip(q_bbox, r_bbox))
    q_area = float(stored_summary["area_m2"])
    r_area = float(rebuilt["area_m2"])
    area_rel = abs(r_area - q_area) / q_area if q_area > 0.0 else float("inf")
    if bbox_delta > tol_m or area_rel > AREA_PARITY_REL:
        raise ProvenanceError(
            "the saved design does not reproducibly regenerate its stored quarter mesh: "
            f"max bbox delta {bbox_delta:.3g} m (tol {tol_m:g}), "
            f"area rel delta {area_rel:.3g} (tol {AREA_PARITY_REL:g}); "
            f"stored bbox {q_bbox}, rebuilt bbox {r_bbox}")
    return ProvenanceGate(
        ok=True, stored_mesh=ref.mesh_path, rebuilt_mesh=rebuilt_path,
        stored_bbox_m=q_bbox, rebuilt_bbox_m=r_bbox, max_abs_bbox_delta_m=bbox_delta,
        stored_area_m2=q_area, rebuilt_area_m2=r_area, area_rel_delta=area_rel,
        stored_triangles=int(stored_summary["n_triangles"]),
        rebuilt_triangles=int(rebuilt["n_triangles"]), tol_m=float(tol_m))


def _sampling_change(original: dict[str, Any], full: dict[str, Any]) -> dict[str, Any]:
    raw_ob = original.get("grid")
    raw_fb = full.get("grid")
    ob: dict[str, Any] = raw_ob if isinstance(raw_ob, dict) else {}
    fb: dict[str, Any] = raw_fb if isinstance(raw_fb, dict) else {}
    changed = {k: [ob.get(k), fb.get(k)] for k in sorted(set(ob) | set(fb))
               if ob.get(k) != fb.get(k) and k != "knobs"}
    return {
        "changed_grid_keys": changed,
        "unchanged_geometry_keys": sorted(
            k for k in set(ob) | set(fb) if ob.get(k) == fb.get(k)),
        "note": ("only the model span and azimuthal sampling change for the full ring; "
                 "profile knobs, n_s and wall thickness are identical"),
    }
