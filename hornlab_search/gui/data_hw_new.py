"""Horn + woofer GUI - P5 new-system backend.

This module is the read-only half of the New system wizard plus the one sanctioned writer
(``save_spec``).  It never meshes, never solves and never launches a job: it turns the real saved
tree and the real sourced driver files into small JSON-ready rows, validates a system spec with the
frozen :func:`hornlab_search.system.contracts.parse_system_spec_dict`, and writes user specs under
``examples/systems/user/`` only after that same parser accepted them.

What comes from where (never mixed):

* **Horns** - :func:`hornlab_search.system.horn_assets.inventory_runs` over ``<root>/runs`` with a
  bounded run-directory count, one :func:`asset_row` per asset.  A "full-domain mesh" is reported
  only when the system store holds a ``ref_case/horn_full`` provenance document naming that
  design hash *and* the recorded ``mesh.msh`` is still present.
* **Drivers** - :func:`hornlab_search.system.woofer_seed.load_driver_catalog`, i.e. the frozen
  cone loader plus the additive geometry schema.  Every T/S number is the vendor YAML's own value;
  Qts is derived from the module's own Qms/Re/Bl/Mms fields (R15) and both numbers carry a
  ``field_sources`` marker so the UI can say which is which.  Nothing is re-typed from a datasheet
  and no missing field is filled in.
* **Defaults** - ``examples/systems/two_way_80x50_700_research.yaml`` parsed through the contract
  parser.  No JS constant and no default is duplicated here.

Hard rules honoured: no invented key/unit, no second schema, no solver/Boundary Lab import, no GPU.
"""
from __future__ import annotations

import copy
import dataclasses
import math
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from hornlab_search.system import contracts as C
from hornlab_search.system import drivers as DRV
from hornlab_search.system import horn_assets as HA
from hornlab_search.system import woofer_seed as W

__all__ = [
    "DEFAULT_SCAN_LIMIT",
    "SCAN_LIMIT_MAX",
    "LIMIT_BOXES_MAX",
    "SHORTLIST_SIZE_MAX",
    "DEFAULT_SPEC_REL",
    "USER_SPEC_DIR",
    "ScreenArgError",
    "hw_assets",
    "hw_drivers",
    "hw_spec_defaults",
    "hw_specs",
    "validate_spec",
    "save_spec",
    "screen_argv",
]

#: Same shape the rest of the system/GUI store uses for one path/name component.
_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
#: ``contracts.domain_sha16`` identities are 16 lowercase hex characters.
_ASSET_ID = re.compile(r"^[0-9a-f]{16}$")
#: First dotted name in a parser message, e.g. ``cabinet.external_width_mm_range``.
_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)")

_ASSET_CACHE: dict[tuple, dict[str, Any]] = {}

DEFAULT_SCAN_LIMIT = 300          # mirrors woofer_seed.main --scan-limit
SCAN_LIMIT_MAX = 5000
LIMIT_BOXES_MAX = 64
SHORTLIST_SIZE_MAX = 64
SCAN_LIMIT_MIN = 1
LIMIT_BOXES_MIN = 1
SHORTLIST_SIZE_MIN = 1
DEFAULT_LIMIT_BOXES = 8         # the recorded 27616eedee09009f screen used --limit-boxes 8
DEFAULT_SHORTLIST_SIZE = W.DEFAULT_SHORTLIST_SIZE

DEFAULT_SPEC_REL = Path("examples/systems/two_way_80x50_700_research.yaml")
USER_SPEC_DIR = Path("examples/systems/user")
DRIVER_TS_DIR = Path("examples/systems/driver_ts")
DRIVER_GEOMETRY_DIR = Path("examples/systems/driver_geometry")

_HEADER = (
    "# User system spec (schema_version 1), written by the Horn + woofer GUI.\n"
    "# Validated by hornlab_search.system.contracts.parse_system_spec_dict before writing;\n"
    "# unknown keys and malformed ranges are refused. Ranges are search bounds, not claims.\n"
)
_R15_NOTE = (
    "field_sources says which value is the vendor YAML's own and which this module derives from "
    "the driver's own fields (R15); it does not re-verify a vendor page."
)


class ScreenArgError(ValueError):
    """A ``hw-screen`` launch request that must be refused; jobs.py re-raises it as JobError."""


class _SpecDumper(yaml.SafeDumper):
    """SafeDumper that keeps the committed example's style: block mappings, flow sequences."""


def _represent_flow_sequence(dumper: yaml.SafeDumper, data: Any):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


_SpecDumper.add_representer(list, _represent_flow_sequence)
_SpecDumper.add_representer(tuple, _represent_flow_sequence)


# --------------------------------------------------------------------------- small helpers


def _root(root: str | Path) -> Path:
    return Path(root).resolve()


def _read_json(path: Path) -> dict | None:
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _label(root: Path, path: str | Path) -> str:
    """Repo-relative when possible, absolute otherwise (never a fabricated path)."""
    p = Path(path)
    try:
        return p.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return p.as_posix()


def _spec_dict(spec: C.SystemSpecV1) -> dict[str, Any]:
    """The parsed spec as a JSON/YAML-ready mapping, with the schema key the parser requires."""
    return {"schema_version": C.SCHEMA_VERSION, **dataclasses.asdict(spec)}


def _field_of(message: str) -> str:
    match = _FIELD.match(str(message))
    if not match:
        return "spec"
    return match.group(1)


def _int_arg(value: Any, lo: int, hi: int, field: str, default: int | None = None) -> int:
    if value in (None, ""):
        if default is None:
            raise ScreenArgError(f"{field}: a value is required")
        return int(default)
    if isinstance(value, bool):
        raise ScreenArgError(f"{field} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ScreenArgError(f"{field} must be an integer") from None
    if not lo <= number <= hi:
        raise ScreenArgError(f"{field} must be in [{lo}, {hi}]")
    return number


# --------------------------------------------------------------------------- horns


def _full_domain_index(store: Path) -> dict[str, dict[str, Any]]:
    """design hash -> recorded full-domain case, only when its mesh is still on disk.

    The provenance document written by ``hornlab_search.system.horn_full_domain`` is read by its
    recorded key ``design_hash_original``.  No schema is imported here on purpose: the GUI read
    path must not import Boundary Lab / mesher modules, and a document without the key is skipped
    (never guessed).
    """
    base = store / "system" / "ref_case" / "horn_full"
    if not base.is_dir():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for prov in sorted(base.glob("*/provenance.json")):
        data = _read_json(prov)
        if not data:
            continue
        design_hash = data.get("design_hash_original")
        mesh = prov.parent / "mesh.msh"
        if not isinstance(design_hash, str) or not design_hash or not mesh.is_file():
            continue
        out[design_hash] = {
            "case_tag": data.get("case_tag") or prov.parent.name,
            "mesh_path": _label(store, mesh),
            "provenance_path": _label(store, prov),
        }
    return out


def hw_assets(root: str | Path, store: str | Path, *, limit: int = DEFAULT_SCAN_LIMIT) -> dict:
    """Saved-horn inventory from ``<root>/runs`` plus the store's full-domain cases.

    Bounded exactly like the CLI's ``--scan-limit`` (newest run dirs only).  Nothing is meshed and
    no response file is modified; unreadable dirs are already classified by ``horn_assets``.
    """
    repo = _root(root)
    store_root = Path(store).resolve()
    runs_root = repo / "runs"
    bounded = max(1, int(limit))
    # Cache by the run tree's mtime + the store's system dir mtime: a new run or case invalidates
    # it. The scan is ~3 s at limit 40, so an uncached per-request scan is not acceptable.
    sys_dir = store_root / "system"
    stamp = (str(repo), str(store_root), bounded,
             runs_root.stat().st_mtime_ns if runs_root.is_dir() else 0,
             sys_dir.stat().st_mtime_ns if sys_dir.is_dir() else 0)
    cached = _ASSET_CACHE.get(stamp)
    if cached is not None:
        return cached

    notes: list[str] = []
    full_index = _full_domain_index(store_root)
    if not runs_root.is_dir():
        notes.append(f"no saved-horn runs tree at {_label(repo, runs_root)}; the inventory is empty")
        result = HA.InventoryResult(str(runs_root), 0, 0, 0, 0, ())
    else:
        result = HA.inventory_runs(runs_root, limit=bounded)
        notes.append(
            f"scanned the newest {result.runs_scanned} run dir(s) under "
            f"{_label(repo, runs_root)} (limit {bounded}); no meshing")

    assets: list[dict[str, Any]] = []
    for asset in result.assets:
        row = HA.asset_row(asset)
        design_hash = row.get("design_hash")
        lo, hi = row.get("freq_lo_hz"), row.get("freq_hi_hz")
        band_hz = [lo, hi] if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) else None
        full = full_index.get(str(design_hash)) if design_hash else None
        run_dir = row.get("run_dir")
        assets.append({
            "asset_id": row.get("asset_id"),
            "name": row.get("brief_id") or row.get("family") or design_hash,
            "brief_id": row.get("brief_id"),
            "design_hash": design_hash,
            "quality": row.get("quality"),
            "band_hz": band_hz,
            "full_domain_mesh": bool(full),
            "runs": [_label(repo, run_dir)] if run_dir else [],
        })

    if result.assets and not full_index:
        notes.append("no ref_case/horn_full provenance in the system store; no full-domain chips")
    if result.skipped_dirs:
        notes.append(f"{result.skipped_dirs} design dir(s) had neither a response nor a mesh")
    out = {"assets": assets, "notes": notes}
    if len(_ASSET_CACHE) >= 8:
        _ASSET_CACHE.pop(next(iter(_ASSET_CACHE)))
    _ASSET_CACHE[stamp] = out
    return out


# --------------------------------------------------------------------------- drivers


def _qts(cone: Any) -> tuple[float | None, str]:
    """Published Qts when the YAML has it, else the module's own Qms/Qes relation."""
    raw = cone.raw if isinstance(getattr(cone, "raw", None), Mapping) else {}
    published = raw.get("qts")
    if isinstance(published, (int, float)) and not isinstance(published, bool):
        return float(published), "vendor"
    if cone.qms is None:
        return None, "missing"
    qes = 2.0 * math.pi * cone.fs_hz * cone.mms_kg * cone.re_ohm / (cone.bl_tm ** 2)
    if not math.isfinite(qes) or qes <= 0.0:
        return None, "derived"
    qts = 1.0 / (1.0 / float(cone.qms) + 1.0 / qes)
    return (qts if math.isfinite(qts) else None), "derived"


def _size_in(cone: Any) -> float | None:
    """Nominal size from the vendor frame OD; ``None`` when the YAML omits it."""
    frame = getattr(cone, "frame_od_mm", None)
    if isinstance(frame, (int, float)) and not isinstance(frame, bool) and frame > 0:
        return round(float(frame) / 25.4, 1)
    return None


def _field_sources(cone: Any, qts_source: str) -> dict[str, str]:
    raw = cone.raw if isinstance(getattr(cone, "raw", None), Mapping) else {}
    vendor = lambda key: "vendor" if raw.get(key) is not None else "derived"  # noqa: E731
    return {
        "name": "vendor",
        "size_in": "derived",
        "fs_hz": vendor("fs_hz"),
        # ConeDriver always computes Vas from Cms; even a printed Vas is round-tripped, so this
        # value is derived here and labelled as such.
        "vas_l": "derived",
        "qts": qts_source,
        "sd_cm2": vendor("sd_cm2"),
        "xmax_mm": vendor("xmax_mm"),
    }


def hw_drivers(root: str | Path, store: str | Path) -> dict:
    """The sourced woofer catalog with honest geometry completeness and R15 provenance."""
    repo = _root(root)
    ts_dir = repo / DRIVER_TS_DIR
    geometry_dir = repo / DRIVER_GEOMETRY_DIR
    notes: list[str] = []
    if not ts_dir.is_dir():
        notes.append(f"no driver T/S directory at {_label(repo, ts_dir)}")
        return {"drivers": [], "notes": notes}

    catalog = W.load_driver_catalog(ts_dir=ts_dir, geometry_dir=geometry_dir)
    for rejected in catalog.rejected:
        notes.append(f"{rejected.get('driver_id')}: {rejected.get('reason')}")
    notes.append(_R15_NOTE)

    drivers: list[dict[str, Any]] = []
    for entry in catalog.entries:
        cone = entry.cone
        qts, qts_source = _qts(cone)
        geometry = entry.driver.geometry_mm
        present = list(entry.present_geometry_fields)
        missing = list(entry.missing_geometry_fields)
        measured_by = None
        geom_urls: list[str] = []
        if entry.geometry_file:
            try:
                doc = DRV.load_driver_geometry(geometry_dir / entry.geometry_file)
            except (OSError, ValueError):
                doc = None
            if doc is not None:
                measured_by = doc.measured_by
                geom_urls = list(doc.sourced_from)
        else:
            geom_urls = list(getattr(geometry, "source_urls", ()) or ())

        drivers.append({
            "driver_id": entry.driver_id,
            "name": cone.name,
            "size_in": _size_in(cone),
            "fs_hz": cone.fs_hz,
            "vas_l": cone.vas_l,
            "qts": qts,
            "sd_cm2": cone.sd_cm2,
            "xmax_mm": cone.xmax_mm,
            "ts_verified": bool(str(cone.source or "").strip()),
            "ts_verified_note": (
                "vendor source URL recorded; the value is not independently measured here"
                if cone.source else "no source URL recorded in the T/S YAML"),
            "geometry": {
                "present_fields": present,
                "missing_fields": missing,
                "complete": not missing,
                "note": ("all installed-surface fields present" if not missing
                         else "missing: " + ", ".join(missing)),
            },
            "provenance": {
                "ts_source": cone.source or None,
                "geometry_source": geom_urls,
                "measured_by": measured_by,
                "ts_file": entry.ts_file,
                "geometry_file": entry.geometry_file,
                "ts_sha256": entry.ts_sha256,
                "geometry_sha256": entry.geometry_sha256,
                "field_sources": _field_sources(cone, qts_source),
            },
        })
    return {"drivers": drivers, "notes": notes}


# --------------------------------------------------------------------------- specs


def hw_spec_defaults(root: str | Path) -> dict:
    """The committed example spec, parsed by the frozen contract parser.

    Returns ``{"source": <repo-relative path>, "spec": <normalised mapping>}``.  The mapping round-
    trips through :func:`parse_system_spec_dict` and is what the wizard shows as defaults.
    """
    repo = _root(root)
    path = repo / DEFAULT_SPEC_REL
    if not path.is_file():
        raise FileNotFoundError(DEFAULT_SPEC_REL.as_posix())
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    spec = C.parse_system_spec_dict(raw)
    return {"source": _label(repo, path), "spec": _spec_dict(spec)}


def hw_specs(root: str | Path) -> dict:
    """Saved user specs under ``examples/systems/user/`` (validated names, parser verdicts)."""
    repo = _root(root)
    base = repo / USER_SPEC_DIR
    notes: list[str] = []
    if not base.is_dir():
        notes.append(f"no user spec directory yet at {USER_SPEC_DIR.as_posix()}")
        return {"specs": [], "notes": notes}
    specs: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.yaml")):
        if not path.is_file() or not _KEY_PART.fullmatch(path.stem) or ".." in path.stem:
            notes.append(f"ignored invalid spec name: {path.name}")
            continue
        entry: dict[str, Any] = {"name": path.stem, "path": _label(repo, path)}
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            spec = C.parse_system_spec_dict(raw)
        except Exception as exc:  # noqa: BLE001 - a broken user file is visible, never skipped
            entry.update(ok=False, experiment_id=None, error=str(exc))
        else:
            entry.update(ok=True, experiment_id=spec.experiment_id, error=None)
        specs.append(entry)
    return {"specs": specs, "notes": notes}


def validate_spec(payload: Mapping[str, Any]) -> dict:
    """Validate one spec mapping through the frozen parser; field-named errors, no invention."""
    if not isinstance(payload, Mapping):
        return {"ok": False,
                "errors": [{"field": "spec",
                            "message": f"spec must be a mapping, got {type(payload).__name__}"}],
                "normalized": None}
    try:
        spec = C.parse_system_spec_dict(payload)
    except (C.SchemaError, C.DataQualityError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, KeyError):
            key = str(exc.args[0]) if exc.args else "spec"
            return {"ok": False,
                    "errors": [{"field": key, "message": f"missing required key: {key}"}],
                    "normalized": None}
        message = str(exc)
        return {"ok": False,
                "errors": [{"field": _field_of(message), "message": message}],
                "normalized": None}
    return {"ok": True, "errors": [], "normalized": _spec_dict(spec)}


def save_spec(root: str | Path, name: str, payload: Mapping[str, Any],
              replace: bool = False) -> str:
    """Write ``examples/systems/user/<name>.yaml`` with LF endings after a parser round-trip.

    Refuses a name outside :data:`_KEY_PART` (so no traversal), any spec the frozen parser rejects
    (the parser's own message is raised), and an existing file unless ``replace`` is true.  Returns
    the repo-relative path.
    """
    repo = _root(root)
    if not isinstance(name, str) or not _KEY_PART.fullmatch(name) or ".." in name:
        raise ScreenArgError(
            "name must match ^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$ and contain no '..'")
    if not isinstance(payload, Mapping):
        raise ScreenArgError(f"spec must be a mapping, got {type(payload).__name__}")

    C.parse_system_spec_dict(payload)          # the parser's own refusal, never a custom schema

    directory = (repo / USER_SPEC_DIR).resolve()
    target = (directory / f"{name}.yaml").resolve()
    if directory not in target.parents:
        raise ScreenArgError("name resolves outside the user spec directory")
    if target.exists() and not replace:
        raise ScreenArgError(
            f"{_label(repo, target)} already exists; pass replace=true to overwrite it")

    directory.mkdir(parents=True, exist_ok=True)
    body = yaml.dump(copy.deepcopy(dict(payload)), Dumper=_SpecDumper, sort_keys=False,
                     allow_unicode=True, default_flow_style=False)
    text = _HEADER + body
    if not text.endswith("\n"):
        text += "\n"
    target.write_text(text, encoding="utf-8", newline="\n")

    # Round-trip the file that will actually be read back.
    written = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    C.parse_system_spec_dict(written)
    return _label(repo, target)


# --------------------------------------------------------------------------- screen launch


def _repo_file(repo: Path, value: Any, field: str, suffix: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise ScreenArgError(f"{field}: a repo-relative {suffix} path is required")
    path = (repo / value.strip()).resolve()
    if repo not in path.parents or path.suffix.lower() != suffix or not path.is_file():
        raise ScreenArgError(f"{field}: not a {suffix} file inside the repository: {value!r}")
    return path, path.relative_to(repo).as_posix()


def _asset_arg(value: Any) -> str:
    if not isinstance(value, str) or not _ASSET_ID.fullmatch(value.strip()):
        raise ScreenArgError(
            "asset_id: a 16-hex saved-horn asset id is required (from the inventory)")
    return value.strip()


def _drivers_arg(repo: Path, value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ScreenArgError("drivers: at least one driver id is required")
    ts_dir = repo / DRIVER_TS_DIR
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _KEY_PART.fullmatch(item.strip()) or ".." in item:
            raise ScreenArgError(f"drivers: invalid driver id {item!r}")
        driver_id = item.strip()
        if not (ts_dir / f"{driver_id}.yaml").is_file():
            raise ScreenArgError(
                f"drivers: unknown driver id {driver_id!r} "
                f"(no {DRIVER_TS_DIR.as_posix()}/{driver_id}.yaml)")
        if driver_id not in out:
            out.append(driver_id)
    if len(out) > 16:
        raise ScreenArgError("drivers: at most 16 driver ids are accepted from the GUI")
    return out


def screen_argv(root: str | Path, payload: Mapping[str, Any], *,
                system_root: str | Path | None = None) -> list[str]:
    """The ``tools/system/gui_system_job.py screen ...`` argv for a validated spec + selection.

    Every argument is checked here (field-named refusals): the spec must be a repository YAML that
    the contract parser accepts, the asset id must be a saved-horn identity, every driver must be
    a real catalog stem, the study label is ``_KEY_PART``-safe, and the integer knobs are bounded.
    ``backend`` is accepted only as ``beat_cpu``; the emitted argv contains no backend/GPU flag at
    all because ``woofer_seed`` is a CPU screen.

    ``study`` is the output directory *label* under ``<store>/screens/`` (default: the spec's own
    ``experiment_id``). The deterministic ``study_id`` is computed by ``woofer_seed`` from the
    inputs and appears in the JSON; pass a distinct label for a deliberate replay so both runs are
    retained (P2 groups them by that recorded id).
    """
    repo = _root(root)
    if not isinstance(payload, Mapping):
        raise ScreenArgError(f"payload must be a mapping, got {type(payload).__name__}")

    backend = payload.get("backend")
    if backend not in (None, ""):
        if str(backend) != "beat_cpu":
            raise ScreenArgError("backend: only beat_cpu is allowed for GUI system screens")

    spec_path, spec_rel = _repo_file(repo, payload.get("spec"), "spec", ".yaml")
    try:
        spec_doc = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        spec = C.parse_system_spec_dict(spec_doc)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        message = str(exc)
        if isinstance(exc, KeyError):
            message = f"missing required key: {exc.args[0] if exc.args else exc}"
        raise ScreenArgError(f"spec: {message}") from None

    asset_id = _asset_arg(payload.get("asset_id"))
    drivers = _drivers_arg(repo, payload.get("drivers"))

    raw_study = payload.get("study")
    study = str(raw_study).strip() if raw_study not in (None, "") else spec.experiment_id
    if not _KEY_PART.fullmatch(study) or ".." in study:
        raise ScreenArgError(
            "study: must match ^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$ and contain no '..'")

    scan_limit = _int_arg(payload.get("scan_limit"), SCAN_LIMIT_MIN, SCAN_LIMIT_MAX,
                          "scan_limit", DEFAULT_SCAN_LIMIT)
    limit_boxes = _int_arg(payload.get("limit_boxes"), LIMIT_BOXES_MIN, LIMIT_BOXES_MAX,
                           "limit_boxes", DEFAULT_LIMIT_BOXES)
    shortlist_size = _int_arg(payload.get("shortlist_size"), SHORTLIST_SIZE_MIN,
                              SHORTLIST_SIZE_MAX, "shortlist_size", DEFAULT_SHORTLIST_SIZE)

    # Do not resolve the store: the canonical ``system_runs`` can be a junction, and keeping the
    # literal repo path lets the preview stay clean. An external absolute store stays absolute.
    store = Path(system_root) if system_root is not None else repo / "system_runs"
    if not store.is_absolute():
        store = repo / store
    target = store / "screens" / study
    try:
        out = target.relative_to(repo).as_posix()
    except ValueError:
        out = target.as_posix()

    return [
        "screen",
        "--spec", spec_rel,
        "--asset-id", asset_id,
        "--drivers", *drivers,
        "--out", out,
        "--runs-root", "runs",
        "--scan-limit", str(scan_limit),
        "--limit-boxes", str(limit_boxes),
        "--shortlist-size", str(shortlist_size),
    ]
