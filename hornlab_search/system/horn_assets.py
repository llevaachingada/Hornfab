"""Read-only inventory of saved horn solves for the ``hornlab_search.system`` layer.

What this module is
--------------------
A read-only adapter over the historical run tree. It discovers design directories that
already hold a saved solve, loads them with the *official* loader
(:func:`hornlab_search.solve.cache.load_response`), and turns each one into a
:class:`hornlab_search.system.contracts.HornAsset`. It never writes: every file is opened
read-only and the system layer's own store (:mod:`hornlab_search.system.provenance`) is the only
sanctioned write target elsewhere.

Runs root
---------
The scanned root is parameterised by the environment variable **``HORNLAB_SYSTEM_RUNS_ROOT``**.
When it is unset the canonical run tree ``C:/Users/hunte/Hrns/hornlab-search/runs`` is used
(:data:`DEFAULT_RUNS_ROOT`). The audit CLI (``tools/system/audit_saved_horns.py``) takes the same
default; ``--runs-root`` overrides both.

Quality rules (phase honesty)
-----------------------------
``EXACT_COMPLEX`` requires **both** an actually-present complex field (``p_h``/``p_v``/
``p_balloon`` with a shape consistent with ``freqs_hz``) **and** a
:class:`~hornlab_search.system.contracts.SourceBasis` proven from stored metadata. The saved
HornFab/beat responses record their basis in ``meta``:

* ``meta["z_throat_convention"]`` carries the time convention (real runs write
  ``"exp(-i*omega*t); ..."``, see ``hornlab_search/solve/beat.py:55``);
* ``meta["spl_reference"]`` names the drive (real runs write ``"absolute dB re 20 uPa for unit
  normal acceleration of tag 2"``, see ``hornlab_search/solve/beat.py:553``).

The system contract requires ``exp(+jomega_t)`` and a per-input basis of ``normal_velocity_mps``
or ``V_rms`` (``contracts.py``). As stored, the canonical solve cache is ``exp(-i omega t)`` and
normalised to unit normal **acceleration** (``hornlab_search/solve/phasor.py:3-9``). No conversion
happens in ``solve/cache.py``. Therefore a saved run whose metadata proves only that native basis
is classified ``MAGNITUDE_ONLY`` with the explicit note "complex fields present, basis unverified —
phase claims refused". Phase is never imputed and hashes are never fabricated.

The derivation accepts only metadata keys that the solvers actually write (``z_throat_convention``,
``spl_reference``, ``distance_m``); it does not invent a new metadata schema. A future import
boundary that truly produced a ``normal_velocity`` / ``exp(+jomega_t)`` field may record that in
those same keys and will then be recognised as ``EXACT_COMPLEX``.

Identity / dedupe
-----------------
Each asset's identity is, in order of preference:

1. ``status.json["physical_solve_id"]`` when present;
2. ``physical_solve_id`` derived from ``status.json["design_hash"|"mesh_hash"|"solve_hash"]``;
3. the ``<design>-<mesh>-<solve>`` triple in ``status.json["key"]``;
4. ``sha256`` of the concatenated ``response.npz`` + ``status.json`` bytes.

Directories that resolve to the same identity are collapsed to one asset (deterministically: the
lexicographically smallest ``response_path`` wins). The public ``asset_id`` is a
domain-separated system identity (``system.horn_asset_v1``), never a reused horn
``physical_solve_id``/``score_id``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from hornlab_search.dataset import identity_v2
from hornlab_search.solve import cache
from hornlab_search.system import contracts as C

__all__ = [
    "DEFAULT_RUNS_ROOT",
    "RUNS_ROOT_ENV",
    "COMPLEX_FIELDS",
    "HORN_ARRAY_FIELDS",
    "PROVENANCE_OK",
    "PROVENANCE_FAILED",
    "PROVENANCE_MISSING",
    "PROVENANCE_GEOMETRY_ONLY",
    "InventoryResult",
    "default_runs_root",
    "inventory_runs",
    "inventory_run",
    "asset_row",
    "derive_source_basis",
]

#: Canonical run tree scanned when the environment variable is unset.
DEFAULT_RUNS_ROOT = "C:/Users/hunte/Hrns/hornlab-search/runs"
#: Environment variable that parameterises the scanned runs root.
RUNS_ROOT_ENV = "HORNLAB_SYSTEM_RUNS_ROOT"

#: The complex pressure fields a horn asset can carry.
COMPLEX_FIELDS: tuple[str, ...] = ("p_h", "p_v", "p_balloon")
#: Horn-response array fields (the MEH additive fields are out of Tier-0 scope).
HORN_ARRAY_FIELDS: tuple[str, ...] = (
    "freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
    "balloon_dirs", "spl_balloon_db", "z_throat", "p_h", "p_v", "p_balloon",
)

PROVENANCE_OK = "status_ok"
PROVENANCE_FAILED = "status_failed"
PROVENANCE_MISSING = "status_missing"
PROVENANCE_GEOMETRY_ONLY = "geometry_only"

_QUALITY_ORDER: tuple[str, ...] = (
    "EXACT_COMPLEX", "MAGNITUDE_ONLY", "GEOMETRY_ONLY", "STALE_SOURCE", "INCOMPATIBLE",
)

_BASIS_UNVERIFIED = "complex fields present, basis unverified \u2014 phase claims refused"


def default_runs_root() -> Path:
    """``$HORNLAB_SYSTEM_RUNS_ROOT`` or the canonical run tree."""
    env = os.environ.get(RUNS_ROOT_ENV, "").strip()
    return Path(env) if env else Path(DEFAULT_RUNS_ROOT)


# --------------------------------------------------------------------------- metadata helpers


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _parse_key(key: Any) -> tuple[str, str, str] | None:
    """``<design_hash>-<mesh_hash>-<solve_hash>`` from a cache key (01_CONTRACTS section 14)."""
    if not isinstance(key, str):
        return None
    parts = key.split("-")
    if len(parts) == 3 and all(parts):
        return parts[0], parts[1], parts[2]
    return None


def _hash_parts(status: Mapping[str, Any] | None,
                design_meta: Mapping[str, Any] | None,
                dir_name: str) -> tuple[str | None, str | None, str | None]:
    design_hash: str | None = None
    mesh_hash: str | None = None
    solve_hash: str | None = None
    if status:
        design_hash = status.get("design_hash") if isinstance(status.get("design_hash"), str) else None
        mesh_hash = status.get("mesh_hash") if isinstance(status.get("mesh_hash"), str) else None
        solve_hash = status.get("solve_hash") if isinstance(status.get("solve_hash"), str) else None
        parsed = _parse_key(status.get("key"))
        if parsed is not None:
            design_hash = design_hash or parsed[0]
            mesh_hash = mesh_hash or parsed[1]
            solve_hash = solve_hash or parsed[2]
    if design_meta and isinstance(design_meta.get("design_hash"), str):
        design_hash = design_hash or design_meta["design_hash"]
    if design_hash is None and len(dir_name) >= 8 and all(c in "0123456789abcdef" for c in dir_name):
        design_hash = dir_name
    return design_hash, mesh_hash, solve_hash


def _stream_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError:
            digest.update(b"<missing>")
        digest.update(b"\x00")
    return digest.hexdigest()


# --------------------------------------------------------------------------- basis evidence


def _parse_time_convention(raw: Any) -> str | None:
    """Map a stored ``z_throat_convention`` string onto the contract time convention.

    Only the two conventions the solvers actually use are recognised; anything else is
    "unproven" (``None``), never guessed.
    """
    if not isinstance(raw, str):
        return None
    text = raw.lower().replace(" ", "")
    if "exp(+i" in text or "exp(+j" in text:
        return C.TIME_CONVENTION
    if "exp(-i" in text or "exp(-j" in text:
        return "exp(-i omega t)"
    return None


def _parse_per_input(meta: Mapping[str, Any]) -> tuple[str | None, str]:
    """Read the drive/normalisation from ``meta["spl_reference"]`` (the only key the solvers write)."""
    reference = meta.get("spl_reference")
    if not isinstance(reference, str) or not reference.strip():
        return None, "spl_reference absent"
    text = reference.lower()
    # Acceleration wins: a string that mentions both is describing the (unsupported) native basis.
    if "acceleration" in text:
        return None, "stored drive is unit normal acceleration"
    if "normal velocity" in text or "normal_velocity" in text:
        return "normal_velocity_mps", ""
    if "v_rms" in text or "rms volt" in text:
        return "V_rms", ""
    return None, f"unrecognised spl_reference {reference!r}"


def _distance_m(meta: Mapping[str, Any]) -> float | None:
    value = meta.get("distance_m")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        distance = float(value)
        if math.isfinite(distance) and distance > 0.0:
            return distance
    return None


def _origin_xyz(meta: Mapping[str, Any]) -> tuple[float, float, float] | None:
    value = meta.get("origin_xyz_m")
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            origin = (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            return None
        if all(math.isfinite(x) for x in origin):
            return origin
    return None


def _angular_frame(available_fields: frozenset[str]) -> str:
    if {"p_h", "p_v"} & available_fields:
        return "hornfab_cuts_hv"
    if "p_balloon" in available_fields:
        return "cartesian_dirs"
    return "unknown"


def derive_source_basis(meta: Mapping[str, Any],
                        available_fields: frozenset[str]) -> tuple[C.SourceBasis | None, str]:
    """Derive a contract :class:`SourceBasis` from stored metadata, or ``(None, reason)``.

    A basis is returned only when the metadata proves *both* the time convention
    (``z_throat_convention``) and the per-input normalisation (``spl_reference``) of the stored
    complex fields. Missing/incompatible evidence yields ``None`` plus a human reason; the caller
    must then classify the asset ``MAGNITUDE_ONLY`` instead of imputing a phase basis.
    """
    per_input, reason = _parse_per_input(meta)
    time_convention = _parse_time_convention(meta.get("z_throat_convention"))
    problems: list[str] = []
    if per_input is None:
        problems.append(reason)
    if time_convention is None:
        problems.append("time convention not proven (z_throat_convention absent/unrecognised)")
    elif time_convention != C.TIME_CONVENTION:
        problems.append(
            f"stored time convention {time_convention!r} != {C.TIME_CONVENTION!r}")
    if problems:
        return None, "; ".join(problems)
    assert per_input is not None and time_convention is not None
    try:
        basis = C.SourceBasis(
            per_input=per_input,  # type: ignore[arg-type]
            time_convention=time_convention,
            distance_m=_distance_m(meta),
            origin_xyz_m=_origin_xyz(meta),
            angular_frame=_angular_frame(available_fields),
        )
    except C.IncompatibleBasis as exc:  # malformed evidence is a refusal, not a crash
        return None, str(exc)
    return basis, ""


# --------------------------------------------------------------------------- field inspection


def _inspect_fields(resp: Any, n_freqs: int) -> tuple[frozenset[str], list[str]]:
    """Return the field names actually present and shape-consistent with ``freqs_hz``."""
    fields: set[str] = {"freqs_hz"}
    issues: list[str] = []

    def take(name: str, arr: Any, *, ndim: int, complex_required: bool = False) -> None:
        if arr is None:
            return
        value = np.asarray(arr)
        if value.ndim != ndim:
            issues.append(f"{name} ndim {value.ndim} != {ndim}")
            return
        if value.shape[0] != n_freqs:
            issues.append(f"{name} shape {value.shape} inconsistent with nf={n_freqs}")
            return
        if complex_required and not np.iscomplexobj(value):
            issues.append(f"{name} is not complex")
            return
        fields.add(name)

    # h/v_angles_deg are the angular axes (length na), not the frequency axis.
    for name, arr in (("h_angles_deg", resp.h_angles_deg), ("v_angles_deg", resp.v_angles_deg)):
        if arr is None:
            continue
        value = np.asarray(arr)
        if value.ndim != 1:
            issues.append(f"{name} ndim {value.ndim} != 1")
        else:
            fields.add(name)

    take("spl_h_db", resp.spl_h_db, ndim=2)
    take("spl_v_db", resp.spl_v_db, ndim=2)
    take("spl_balloon_db", resp.spl_balloon_db, ndim=2)
    take("z_throat", resp.z_throat, ndim=1, complex_required=True)
    take("p_h", resp.p_h, ndim=2, complex_required=True)
    take("p_v", resp.p_v, ndim=2, complex_required=True)
    take("p_balloon", resp.p_balloon, ndim=2, complex_required=True)

    # balloon_dirs is (n_directions, 3): its leading axis is the direction count, not nf.
    if resp.balloon_dirs is not None:
        value = np.asarray(resp.balloon_dirs)
        if value.ndim != 2 or value.shape[1] != 3:
            issues.append(f"balloon_dirs shape {value.shape} is not (n, 3)")
        else:
            fields.add("balloon_dirs")
    return frozenset(fields), issues


# --------------------------------------------------------------------------- one design dir


@dataclass(frozen=True)
class _RunMetadata:
    family: str | None
    brief_id: str | None
    objective_version: str | None


def _run_metadata(raw: Mapping[str, Any] | None) -> _RunMetadata:
    if not raw:
        return _RunMetadata(None, None, None)
    config = raw.get("config") if isinstance(raw.get("config"), Mapping) else {}
    brief = config.get("brief") if isinstance(config, Mapping) else None
    brief_id = None
    if isinstance(brief, Mapping) and isinstance(brief.get("name"), str):
        brief_id = brief["name"]
    family = raw.get("family") if isinstance(raw.get("family"), str) else None
    objective = raw.get("objective_version")
    return _RunMetadata(
        family=family,
        brief_id=brief_id,
        objective_version=None if objective is None else str(objective),
    )


def _build_asset(design_dir: Path, run_dir: Path, run_meta: _RunMetadata) -> C.HornAsset | None:
    response_path = design_dir / cache.RESPONSE_FILE
    status_path = design_dir / cache.STATUS_FILE
    mesh_path = design_dir / "mesh.msh"
    status = _read_json(status_path)
    design_meta = _read_json(design_dir / "design.json")

    has_response = response_path.is_file()
    has_mesh = mesh_path.is_file()
    if not has_response and not has_mesh:
        return None

    provenance = PROVENANCE_GEOMETRY_ONLY
    if status is not None and status.get("ok") is True:
        provenance = PROVENANCE_OK
    elif status is not None and status.get("ok") is False:
        provenance = PROVENANCE_FAILED
    elif has_response:
        provenance = PROVENANCE_MISSING

    design_hash, mesh_hash, solve_hash = _hash_parts(status, design_meta, design_dir.name)

    physical_solve_id: str | None = None
    if status is not None and isinstance(status.get("physical_solve_id"), str):
        physical_solve_id = status["physical_solve_id"]
    elif design_hash and mesh_hash and solve_hash:
        physical_solve_id = identity_v2.physical_solve_id(design_hash, mesh_hash, solve_hash)

    response_sha256: str | None = None
    geometry_sha256: str | None = None
    if physical_solve_id is not None:
        identity = physical_solve_id
    elif has_response:
        response_sha256 = _stream_sha256((response_path, status_path))
        identity = f"content:{response_sha256}"
    else:
        geometry_sha256 = _stream_sha256((mesh_path, design_dir / "design.json"))
        identity = f"geometry:{geometry_sha256}"
    if design_hash is None:
        design_hash = response_sha256 or geometry_sha256 or identity

    family = design_meta.get("family") if isinstance(design_meta, Mapping) else None
    if not isinstance(family, str):
        family = run_meta.family

    quality: str
    data_quality: str
    freqs: tuple[float, ...] = ()
    fields: frozenset[str] = frozenset()
    source_basis: C.SourceBasis | None = None
    issues: list[str] = []

    if has_response:
        try:
            resp = cache.load_response(response_path)
            raw_freqs = np.asarray(resp.freqs_hz, dtype=float).reshape(-1)
            if raw_freqs.size == 0 or not np.all(np.isfinite(raw_freqs)):
                raise ValueError("freqs_hz is empty or non-finite")
            freqs = tuple(float(x) for x in raw_freqs)
            fields, issues = _inspect_fields(resp, len(freqs))
            meta = resp.meta if isinstance(resp.meta, Mapping) else {}
        except Exception as exc:  # noqa: BLE001 - unreadable response is a classified asset
            resp = None
            meta = {}
            data_quality = f"response.npz unreadable: {exc}"
            quality = "INCOMPATIBLE"
        else:
            if issues:
                quality = "INCOMPATIBLE"
                data_quality = "malformed response arrays: " + "; ".join(issues)
            elif provenance == PROVENANCE_FAILED:
                quality = "STALE_SOURCE"
                error = status.get("error") if status else ""
                data_quality = f"status.json ok=false: {error or 'no error text'}"
            elif provenance == PROVENANCE_MISSING:
                quality = "STALE_SOURCE"
                data_quality = "status.json absent: source freshness unverified"
            elif not (fields & set(COMPLEX_FIELDS)) and not (
                    {"spl_h_db", "spl_v_db", "spl_balloon_db", "z_throat"} & fields):
                quality = "GEOMETRY_ONLY"
                data_quality = "response has no acoustic magnitude or complex field"
            elif fields & set(COMPLEX_FIELDS):
                source_basis, reason = derive_source_basis(meta, fields)
                if source_basis is not None:
                    quality = "EXACT_COMPLEX"
                    data_quality = "complex fields present; SourceBasis proven from stored metadata"
                else:
                    quality = "MAGNITUDE_ONLY"
                    data_quality = f"{_BASIS_UNVERIFIED}; {reason}"
            else:
                quality = "MAGNITUDE_ONLY"
                data_quality = "magnitude-only fields present; no complex p_* arrays"
    else:
        quality = ("STALE_SOURCE" if provenance == PROVENANCE_FAILED else "GEOMETRY_ONLY")
        data_quality = ("mesh present but no response.npz; status.json ok=false"
                        if quality == "STALE_SOURCE"
                        else "geometry/mesh only; no response.npz")

    band_hz = (freqs[0], freqs[-1]) if freqs else None
    geometry = C.GeometryMetadata(
        family=family if isinstance(family, str) else None,
        brief_id=run_meta.brief_id,
        physical_solve_id=physical_solve_id,
        analysis_id=None,
        score_id=None,
        objective_version=run_meta.objective_version,
        mesh_sha256=None,
        run_dir=str(run_dir),
        band_hz=band_hz,
        source_urls=(),
        extra={
            "identity": identity,
            "design_dir": str(design_dir),
            "provenance": provenance,
            "data_quality": data_quality,
            "response_sha256": response_sha256,
            "geometry_sha256": geometry_sha256,
            "mesh_present": has_mesh,
            "response_present": has_response,
        },
    )
    asset_id = C.domain_sha16("system.horn_asset_v1", {"identity": identity})
    return C.HornAsset(
        asset_id=asset_id,
        design_hash=design_hash,
        response_path=str(response_path),
        mesh_path=str(mesh_path) if has_mesh else None,
        geometry=geometry,
        available_fields=fields,
        quality=quality,  # type: ignore[arg-type]
        freqs_hz=freqs,
        source_basis=source_basis,
    )


# --------------------------------------------------------------------------- inventory


@dataclass(frozen=True)
class InventoryResult:
    """The deterministic result of scanning a runs root."""

    runs_root: str
    runs_scanned: int
    design_dirs_scanned: int
    skipped_dirs: int
    duplicates_collapsed: int
    assets: tuple[C.HornAsset, ...]

    def quality_counts(self) -> dict[str, int]:
        counts = {name: 0 for name in _QUALITY_ORDER}
        for asset in self.assets:
            counts[asset.quality] = counts.get(asset.quality, 0) + 1
        return counts

    def with_complex_fields(self) -> int:
        return sum(1 for a in self.assets if set(a.available_fields) & set(COMPLEX_FIELDS))

    def with_complex_hv(self) -> int:
        return sum(1 for a in self.assets if {"p_h", "p_v"} <= set(a.available_fields))

    def with_complex_balloon(self) -> int:
        return sum(1 for a in self.assets if "p_balloon" in a.available_fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs_root": self.runs_root,
            "runs_scanned": self.runs_scanned,
            "design_dirs_scanned": self.design_dirs_scanned,
            "skipped_dirs": self.skipped_dirs,
            "duplicates_collapsed": self.duplicates_collapsed,
            "assets_total": len(self.assets),
            "by_quality": self.quality_counts(),
            "with_complex_fields": self.with_complex_fields(),
            "with_complex_hv": self.with_complex_hv(),
            "with_complex_balloon": self.with_complex_balloon(),
            "rows": [asset_row(asset) for asset in self.assets],
        }


def asset_row(asset: C.HornAsset) -> dict[str, Any]:
    """The deterministic, JSON-ready row for one asset (no wall-clock fields)."""
    lo = asset.freqs_hz[0] if asset.freqs_hz else None
    hi = asset.freqs_hz[-1] if asset.freqs_hz else None
    basis = asset.source_basis
    return {
        "asset_id": asset.asset_id,
        "design_hash": asset.design_hash,
        "physical_solve_id": asset.geometry.physical_solve_id,
        "quality": asset.quality,
        "family": asset.geometry.family,
        "brief_id": asset.geometry.brief_id,
        "run_dir": asset.geometry.run_dir,
        "response_path": asset.response_path,
        "mesh_path": asset.mesh_path,
        "n_freqs": len(asset.freqs_hz),
        "freq_lo_hz": lo,
        "freq_hi_hz": hi,
        "available_fields": sorted(asset.available_fields),
        "has_complex_hv": {"p_h", "p_v"} <= set(asset.available_fields),
        "has_complex_balloon": "p_balloon" in asset.available_fields,
        "source_basis": None if basis is None else {
            "per_input": basis.per_input,
            "time_convention": basis.time_convention,
            "quantity": basis.quantity,
            "distance_m": basis.distance_m,
            "origin_xyz_m": list(basis.origin_xyz_m) if basis.origin_xyz_m else None,
            "angular_frame": basis.angular_frame,
            "source_geometry_hash": basis.source_geometry_hash,
        },
        "provenance": asset.geometry.extra.get("provenance"),
        "data_quality": asset.geometry.extra.get("data_quality"),
        "response_sha256": asset.geometry.extra.get("response_sha256"),
        "geometry_sha256": asset.geometry.extra.get("geometry_sha256"),
    }


def _is_single_run(root: Path) -> bool:
    return (root / "designs").is_dir() or (root / cache.RESPONSE_FILE).is_file()


def _run_dirs(root: Path, limit: int | None) -> list[Path]:
    if _is_single_run(root):
        dirs = [root]
    else:
        dirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
        dirs.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return dirs if limit is None else dirs[: max(0, limit)]


def _design_dirs(run_dir: Path) -> list[Path]:
    designs = run_dir / "designs"
    if designs.is_dir():
        return sorted((d for d in designs.iterdir() if d.is_dir()), key=lambda p: p.name)
    if (run_dir / cache.RESPONSE_FILE).is_file() or (run_dir / "mesh.msh").is_file():
        return [run_dir]
    return []


def inventory_run(run_dir: str | os.PathLike[str]) -> list[C.HornAsset]:
    """Inventory one run directory (``<run>/designs/<design_hash>/`` or a flat design dir)."""
    run_path = Path(run_dir)
    run_meta = _run_metadata(_read_json(run_path / "run.json"))
    assets: list[C.HornAsset] = []
    for design_dir in _design_dirs(run_path):
        asset = _build_asset(design_dir, run_path, run_meta)
        if asset is not None:
            assets.append(asset)
    return assets


def inventory_runs(root: str | os.PathLike[str] | None = None,
                   *, limit: int | None = None) -> InventoryResult:
    """Read-only inventory of ``root`` (newest ``limit`` run directories by mtime).

    ``root`` may be a runs tree (subdirectories are runs) or a single run directory. ``limit=None``
    scans every run; the CLI passes its ``--limit``. Nothing is written; every file is opened
    read-only by the official cache loader.
    """
    runs_root = Path(root) if root is not None else default_runs_root()
    if not runs_root.is_dir():
        return InventoryResult(str(runs_root), 0, 0, 0, 0, ())

    run_dirs = _run_dirs(runs_root, limit)
    seen: dict[str, C.HornAsset] = {}
    design_dirs_scanned = 0
    skipped = 0
    duplicates = 0

    for run_dir in run_dirs:
        run_meta = _run_metadata(_read_json(run_dir / "run.json"))
        for design_dir in _design_dirs(run_dir):
            design_dirs_scanned += 1
            asset = _build_asset(design_dir, run_dir, run_meta)
            if asset is None:
                skipped += 1
                continue
            identity = str(asset.geometry.extra["identity"])
            previous = seen.get(identity)
            if previous is None:
                seen[identity] = asset
            else:
                duplicates += 1
                if asset.response_path < previous.response_path:
                    seen[identity] = asset

    assets = tuple(sorted(seen.values(), key=lambda a: a.asset_id))
    return InventoryResult(
        runs_root=str(runs_root),
        runs_scanned=len(run_dirs),
        design_dirs_scanned=design_dirs_scanned,
        skipped_dirs=skipped,
        duplicates_collapsed=duplicates,
        assets=assets,
    )
