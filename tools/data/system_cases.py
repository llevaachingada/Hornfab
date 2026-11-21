"""Export the HORN + VENTED-WOOFER SYSTEM solve/screen data as a portable, regenerable bundle.

``system_runs/`` is git-ignored, so a cloud agent cannot read the system study.  This tool writes
a self-describing export under ``--out`` (default ``docs/system_data``):

* ``system_cases.csv``    - one flat row per system case (experiment x timestamped case dir), with
                            status, gate, run provenance, box/horn numbers, clearance verdict and
                            the readiness declarations joined by case key.
* ``system_cases.json``   - the same rows with nested run detail, the scan census, the readiness
                            registry block, and a ``diagnostics`` list for unreadable cases.
* ``system_screens.json`` - every ``system_runs/**/woofer_seed.json`` screen: study id, counts,
                            input hashes, envelope and the shortlist rows verbatim.

This is the system-study counterpart to :mod:`tools.data.top_designs` (``docs/top_designs``), which
exports the pure-horn GPU design/solve ranking.  They are deliberately separate: the system tree
has no objective J to rank and its fidelity labels are *declared* in
``docs/research/system_woofer_2026-11-18/readiness.yaml``, never inferred from a manifest.

What comes from where (never mixed):

* **Facts** - solved / staged / refused / invalid, frequencies, backend, box dimensions, horn
  offset, clearance verdict, driver name, hashes and integrity - are read from the case directory
  (``manifest.json``, ``run/manifest.json``, and the case's project/request/stage JSON).
* **Declarations** - fidelity, transducer shape, gate name, ref, evidence, pair_with - come only
  from the readiness registry.  A case missing from it is ``UNDECLARED``; nothing is inferred.
  ``motor`` additionally falls back to an observed manifest fact (``motor_mapping`` /
  ``motor_role`` present => ``real``) and says so in ``motor_source``.

Only the standard library is required (``argparse``/``csv``/``json``/``pathlib``/``hashlib``/
``datetime``).  PyYAML is a declared project dependency and is imported behind a guard; without it
the declarations degrade to ``UNDECLARED`` and a diagnostic is emitted.

Read-only over ``system_runs/``; the only writes are the files under ``--out``.  No solver, no
Boundary Lab module, no subprocess, no network.

Usage (from the repository root)::

    .venv\\Scripts\\python.exe tools\\data\\system_cases.py
    .venv\\Scripts\\python.exe tools\\data\\system_cases.py --root . --out docs/system_data --pretty
    .venv\\Scripts\\python.exe tools\\data\\system_cases.py --no-screens --no-csv
    .venv\\Scripts\\python.exe tools\\data\\system_cases.py --strict   # exit 1 on any diagnostic

Status rules (priority order, first match wins):

1. ``solved``   - ``run/manifest.json`` exists and its ``status`` is ``complete``.
2. ``refused``  - a case-level refusal: ``payload.result.ok is False`` with a refusal error
                  (driver/port clearance, panel fit, "does not fit"), a ``refused: true``, or a
                  ``REFUSED`` / ``BL_*REFUS*`` token in a payload string.
3. ``staged``   - a readable manifest with no complete run.
4. ``invalid``  - missing/unparseable manifest or an unreadable case dir (never crashes).

A bare ``spec.geometry.refusals`` field ledger (``GEOMETRY_FIELD_UNAVAILABLE``) and the generic
``BL_CAPABILITY_OK`` status are **not** case refusals; only a case-level refusal counts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

TOOL = "system_cases"
SCHEMA_VERSION = 1

#: The committed readiness registry (declarations only; status facts never come from here).
READINESS_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")

#: Registry schemas this loader understands: v1 inline ``cases``, v2 ``cases.d/*.yaml``.
REGISTRY_SCHEMAS = ("hw_readiness_v1", "hw_readiness_v2")

#: v2 case declarations live in this folder beside the registry, never anywhere else.
CASE_FILES_DIR = "cases.d"

#: A case directory is a UTC timestamp prefix (``20261118T225108Z-...``).
CASE_DIR_RE = re.compile(r"^\d{8}T\d{6}Z")

#: Experiment/case path parts that are not study records.
SKIP_PARTS = frozenset({"_fixtures", "__pycache__", ".git"})

#: Explicit override hook for a case the operator knows is refused but whose manifest lost the
#: token.  Empty by default: status facts stay in the case dir.
KNOWN_REFUSED: frozenset[str] = frozenset()

#: Error text that marks a BL generator/validator *refusal* (not an adapter crash).
REFUSAL_PHRASES = (
    "refus",
    "must fit inside",
    "must not overlap",
    "does not fit",
    "panel-fit",
    "panel fit",
    "exceeds the panel",
)

#: ``REFUSED`` or a refusal-shaped ``BL_*`` token.  ``BL_CAPABILITY_OK`` is deliberately excluded.
REFUSAL_TOKEN_RE = re.compile(
    r"\bREFUSED\b"
    r"|\bBL_[A-Z0-9_]*(?:REFUS|REJECT|BLOCK|UNAVAIL|INCOMPATIBLE)[A-Z0-9_]*\b"
)

#: Flat CSV columns, in stable order.  ``source_path`` is repo-relative (no absolute paths).
CASE_CSV_FIELDS = (
    "experiment",
    "case",
    "case_key",
    "created_utc",
    "kind",
    "gate",
    "gate_source",
    "ref",
    "status",
    "solved",
    "n_frequencies",
    "freq_min_hz",
    "freq_max_hz",
    "backend_id",
    "solve_kind",
    "phasor_convention",
    "completion",
    "authorized_by",
    "fidelity",
    "motor",
    "motor_source",
    "transducer_shape",
    "horn_source",
    "pair_with",
    "project_sha256",
    "project_integrity",
    "run_manifest_sha256",
    "run_manifest_integrity",
    "request_sha256",
    "request_integrity",
    "manifest_payload_sha256",
    "manifest_integrity",
    "box_width_mm",
    "box_height_mm",
    "box_depth_mm",
    "net_volume_l",
    "net_volume_source",
    "port_area_cm2",
    "tuning_hz",
    "horn_mesh",
    "horn_mesh_sha256",
    "horn_offset_mm",
    "horn_offset_mm_xyz",
    "clearance_status",
    "clearance_min_mm",
    "driver_name",
    "evidence",
    "notes",
    "declared",
    "run_status",
    "stage_ok",
    "stage_error",
    "source_path",
)

CASE_NAMES = {
    "csv": "system_cases.csv",
    "json": "system_cases.json",
    "screens": "system_screens.json",
}


# --------------------------------------------------------------------------- small helpers


def _finite(value: object) -> float | None:
    """A finite float or ``None`` (bools are not numbers)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _num(value: object) -> float | None:
    """A float from a JSON number or a numeric string, else ``None``."""
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return None
    return _finite(value)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _mm_from_m(value: object) -> float | None:
    metres = _num(value)
    return None if metres is None else round(metres * 1000.0, 3)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rel(path: Path, root: Path) -> str:
    """Repo-relative POSIX path, or the bare name when the path escapes ``root``.

    ``system_runs/`` may be a junction/symlink outside the checkout, so symlinks are *not*
    resolved for the relative-path calculation (``os.path.abspath`` keeps the logical path).
    """
    try:
        return Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root))).as_posix()
    except ValueError:
        pass
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return path.name


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        return None


def _clean(value: Any) -> Any:
    """JSON-safe recursively; non-finite floats become ``None``."""
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_clean(value), sort_keys=True, separators=(",", ":"))
    return value


# --------------------------------------------------------------------------- manifest hashing
#
# The system manifest writer canonicalises the payload with
# ``hornlab_search.system.contracts.canonical_json`` and re-parses JSON-encoded payload values
# before hashing (``hornlab_search.system.provenance.load_manifest``).  Both are reproduced here
# with the standard library so this tool never imports the solver/system packages.


def _canonical_obj(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 12)
    if isinstance(value, dict):
        return {str(k): _canonical_obj(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical_obj(item) for item in value]
    return str(value)


def canonical_json(value: Any) -> str:
    """Stable JSON for hashing: sorted keys, floats rounded to 12, compact separators."""
    return json.dumps(_canonical_obj(value), sort_keys=True, separators=(",", ":"))


def reparse_payload(payload: object) -> dict:
    """``payload`` with JSON-encoded dict/list strings parsed once (the ``load_manifest`` rule)."""
    if not isinstance(payload, dict):
        return {}
    parsed: dict = {}
    for key, value in payload.items():
        if isinstance(value, str) and value[:1] in ("{", "["):
            try:
                parsed[key] = json.loads(value)
                continue
            except ValueError:
                pass
        parsed[key] = value
    return parsed


def payload_sha256(payload: dict) -> str:
    return hashlib.sha256(canonical_json(reparse_payload(payload)).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> tuple[Any, str | None]:
    """``(data, error)``; never raises."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _deep_parse(value: Any, depth: int = 0) -> Any:
    """Recursively parse JSON-encoded strings (the manifests store blocks as JSON strings)."""
    if depth > 6:
        return value
    if isinstance(value, str) and value[:1] in ("{", "["):
        try:
            return _deep_parse(json.loads(value), depth + 1)
        except ValueError:
            return value
    if isinstance(value, dict):
        return {key: _deep_parse(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_parse(item, depth + 1) for item in value]
    return value


def _walk_dicts(obj: Any, path: tuple[str, ...] = (), depth: int = 0) -> Iterable[tuple[tuple[str, ...], dict]]:
    """Every dict in the tree with its key path, root first (defensive: any shape)."""
    if depth > 24:
        return
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from _walk_dicts(value, path + (str(key),), depth + 1)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            yield from _walk_dicts(item, path + (str(index),), depth + 1)


# --------------------------------------------------------------------------- metadata extraction


def _find_first(docs: list[tuple[str, Any]], *keys: str) -> tuple[Any, str | None]:
    """First scalar value for any of ``keys``, in document priority order."""
    for label, doc in docs:
        for path, node in _walk_dicts(doc):
            for key in keys:
                if key in node:
                    value = node[key]
                    if not isinstance(value, (dict, list)):
                        return value, label
    return None, None


def _find_path_value(docs: list[tuple[str, Any]], *suffixes: tuple[str, ...]) -> Any:
    """First scalar at a key path ending with one of ``suffixes`` (e.g. ``("mapping", "driver_id")``)."""
    for _label, doc in docs:
        for path, node in _walk_dicts(doc):
            for suffix in suffixes:
                key = suffix[-1]
                if key not in node or isinstance(node[key], (dict, list)):
                    continue
                expected = suffix[:-1]
                if not expected or (len(path) >= len(expected) and tuple(path[-len(expected):]) == expected):
                    value = node[key]
                    if _text(value).strip():
                        return value
    return None


def _driver_name(docs: list[tuple[str, Any]]) -> str | None:
    """A driver identifier from any declared shape, preferring a human vendor name."""
    value = _find_first(docs, "driver_name")[0]
    if not _text(value).strip():
        value = _find_path_value(docs, ("mapping", "driver_id"))
    if not _text(value).strip():
        value = _find_path_value(docs, ("driver", "yaml", "name"))
    if not _text(value).strip():
        value = _find_path_value(docs, ("driver", "name"))
    if not _text(value).strip():
        value = _find_first(docs, "driver_id")[0]
    return _text(value).strip() or None


def _find_box_source(docs: list[tuple[str, Any]]) -> tuple[dict | None, str | None]:
    """First dict declaring a complete ``width_m``/``height_m``/``depth_m`` box."""
    for label, doc in docs:
        for _path, node in _walk_dicts(doc):
            if all(key in node for key in ("width_m", "height_m", "depth_m")):
                return node, label
    return None, None


def _find_horn(docs: list[tuple[str, Any]]) -> tuple[dict | None, str | None]:
    """First horn block: a dict with ``translation_mm`` plus a mesh reference."""
    for label, doc in docs:
        for path, node in _walk_dicts(doc):
            if "translation_mm" in node and any(
                key in node for key in ("mesh_path", "mesh_file", "mesh_role", "source_group")
            ):
                return node, label
        for _path, node in _walk_dicts(doc):
            horn = node.get("horn")
            if isinstance(horn, dict) and horn:
                return horn, label
    return None, None


def _find_clearance_record(docs: list[tuple[str, Any]]) -> tuple[dict | None, str | None]:
    """An explicit clearance verdict only (never a seeded placement gap scan)."""
    for label, doc in docs:
        for path, node in _walk_dicts(doc):
            if path and path[-1] == "clearance" and isinstance(node, dict):
                return node, label
            joined = ".".join(path).lower()
            if "clearance" in joined and any(
                key in node for key in ("status", "ok", "min_gap_m", "clearance_m", "min_clearance_mm")
            ):
                return node, label
    return None, None


def _clearance_verdict(
    record: dict | None,
    label: str | None,
    *,
    has_metadata: bool,
) -> tuple[str, float | None, str | None]:
    """``(status, min_gap_mm, source)`` from a recorded clearance block, never inferred."""
    if record is None:
        return ("not_recorded" if has_metadata else "unknown"), None, None
    minimum = None
    for key in ("min_gap_m", "clearance_m", "min_clearance_m"):
        metres = _num(record.get(key))
        if metres is not None:
            minimum = round(metres * 1000.0, 3)
            break
    if minimum is None:
        minimum = _num(record.get("min_clearance_mm"))
    raw = _text(record.get("status")).strip().upper()
    if raw in {"PASS", "OK", "PASSED"}:
        status = "pass"
    elif raw in {"FAIL", "FAILED", "VIOLATION", "REJECTED", "BLOCKED"}:
        status = "violation"
    elif raw in {"NOT_CHECKED", "NOT-RECORDED", "UNKNOWN"}:
        status = "not_recorded"
    elif record.get("ok") is True:
        status = "pass"
    elif record.get("ok") is False:
        status = "violation"
    else:
        status = "not_recorded"
    return status, minimum, label


def _metadata_documents(case: Path, payload: dict) -> list[tuple[str, Any]]:
    """Ordered metadata sources: the four named files first, then the case's own side-cars.

    A staged case has no ``run/`` tree, so the adapter/stage reports are the only place the box,
    horn and driver declarations exist.  They are read last-but-one and the manifest payload is
    the final fallback; every source is named so a null can be traced.
    """
    ordered = [
        "request.json",
        "run/request.json",
        "run/compiled-system.json",
        "run/project.snapshot.blab.json",
        "adapter_spec.json",
        "case.blab.json",
        "stage_report.json",
        "driver_patch_report.json",
    ]
    docs: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for rel in ordered:
        seen.add(rel)
        path = case / rel
        data, _error = _read_json(path)
        if data is not None:
            docs.append((rel, _deep_parse(data)))
    for path in sorted(case.glob("*.json")):
        name = path.name
        if name in seen or name == "manifest.json":
            continue
        if "request" not in name.lower() and "spec" not in name.lower():
            continue
        data, _error = _read_json(path)
        if data is not None:
            docs.append((name, _deep_parse(data)))
    if payload:
        docs.append(("manifest.payload", _deep_parse(payload)))
    return docs


def _metadata(case: Path, payload: dict) -> dict:
    """Defensive per-field extraction; absent keys become ``None``."""
    docs = _metadata_documents(case, payload)
    box, box_source = _find_box_source(docs)
    horn, horn_source = _find_horn(docs)
    clearance, clearance_source = _find_clearance_record(docs)

    width = height = depth = None
    port_area_cm2 = None
    if box is not None:
        width = _mm_from_m(box.get("width_m"))
        height = _mm_from_m(box.get("height_m"))
        depth = _mm_from_m(box.get("depth_m"))

    declared_port_cm2 = _num(_find_first(docs, "port_throat_area_cm2")[0])
    if declared_port_cm2 is not None:
        port_area_cm2 = round(declared_port_cm2, 3)
    else:
        port_area_m2 = _num(_find_first(docs, "port_area_m2")[0])
        if port_area_m2 is not None:
            port_area_cm2 = round(port_area_m2 * 1e4, 3)

    net_volume_l = _num(_find_first(docs, "net_volume_l")[0])
    net_volume_source = "declared" if net_volume_l is not None else None
    if net_volume_l is None:
        air_volume_m3 = _num(_find_first(docs, "air_volume_m3")[0])
        if air_volume_m3 is not None:
            net_volume_l = round(air_volume_m3 * 1000.0, 3)
            net_volume_source = "air_volume_m3"
    if net_volume_l is not None:
        net_volume_l = round(net_volume_l, 3)

    horn_mesh = None
    horn_mesh_sha256 = None
    horn_offset_mm = None
    horn_offset_xyz = None
    if horn is not None:
        for key in ("mesh_sha256",):
            value = _text(horn.get(key))
            if value:
                horn_mesh_sha256 = value
        for key in ("mesh_path", "mesh_file"):
            value = _text(horn.get(key))
            if value:
                horn_mesh = Path(value).parent.name or Path(value).name
                break
        if horn_mesh is None:
            horn_mesh = _text(horn.get("mesh_name")) or _text(horn.get("name")) or None
        raw_translation = horn.get("translation_mm")
        if isinstance(raw_translation, (list, tuple)):
            components = [_num(item) for item in raw_translation]
            if components and all(item is not None for item in components):
                values = [float(item) for item in components if item is not None]
                horn_offset_xyz = [round(value, 3) for value in values]
                horn_offset_mm = round(max(abs(value) for value in values), 3)

    clearance_status, clearance_min_mm, _ = _clearance_verdict(
        clearance,
        clearance_source,
        has_metadata=bool(docs),
    )

    driver_name = _driver_name(docs)

    tuning_hz = _num(_find_first(docs, "tuning_hz")[0])

    return {
        "box_width_mm": width,
        "box_height_mm": height,
        "box_depth_mm": depth,
        "box_source": box_source,
        "net_volume_l": net_volume_l,
        "net_volume_source": net_volume_source,
        "port_area_cm2": port_area_cm2,
        "tuning_hz": None if tuning_hz is None else round(tuning_hz, 3),
        "horn_mesh": horn_mesh,
        "horn_mesh_sha256": horn_mesh_sha256,
        "horn_offset_mm": horn_offset_mm,
        "horn_offset_mm_xyz": horn_offset_xyz,
        "clearance_status": clearance_status,
        "clearance_min_mm": clearance_min_mm,
        "clearance_source": clearance_source,
        "driver_name": driver_name,
        "metadata_sources": [label for label, _doc in docs],
    }


# --------------------------------------------------------------------------- case scan


def _refusal_reason(payload: dict, case_key: str) -> str | None:
    """A case-level refusal reason, else ``None`` (field ledgers and BL_CAPABILITY_OK excluded)."""
    if case_key in KNOWN_REFUSED:
        return "known-refused"
    result = payload.get("result")
    if isinstance(result, str):
        parsed, _error = _read_json_str(result)
        result = parsed
    if isinstance(result, dict) and result.get("ok") is False:
        error = _text(result.get("error")).strip()
        lowered = error.lower()
        if error and any(phrase in lowered for phrase in REFUSAL_PHRASES):
            return error
    if payload.get("refused") is True:
        return "refused: true"
    for match in REFUSAL_TOKEN_RE.finditer(_flatten_strings(payload)):
        return match.group(0)
    return None


def _read_json_str(text: str) -> tuple[Any, str | None]:
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _flatten_strings(value: Any, depth: int = 0) -> str:
    """All string values joined (keys are not scanned; a field ledger key must not trip this)."""
    if depth > 8:
        return ""
    if isinstance(value, str):
        return value + "\n"
    if isinstance(value, dict):
        return "".join(_flatten_strings(item, depth + 1) for item in value.values())
    if isinstance(value, (list, tuple)):
        return "".join(_flatten_strings(item, depth + 1) for item in value)
    return ""


def _run_detail(case: Path, payload: dict) -> dict:
    """``run/manifest.json`` facts plus the recorded run block from ``payload.run``."""
    recorded_raw = payload.get("run")
    recorded = reparse_payload({"run": recorded_raw})["run"] if recorded_raw else None
    if not isinstance(recorded, dict):
        recorded = {}

    detail: dict = {
        "present": False,
        "manifest_sha256": None,
        "manifest_integrity": "unknown",
        "status": recorded.get("status"),
        "backend_id": recorded.get("backend_id"),
        "solve_kind": recorded.get("solve_kind"),
        "phasor_convention": recorded.get("phasor_convention"),
        "frequencies_hz": recorded.get("frequencies_hz"),
        "excitation_port_ids": recorded.get("excitation_port_ids"),
        "schema": None,
        "schema_version": None,
        "started_at_utc": None,
        "finished_at_utc": None,
        "solver_options": None,
        "engine_runs": [],
        "meshes": [],
        "completion_mask": None,
    }
    path = case / "run" / "manifest.json"
    if not path.is_file():
        return detail
    data, error = _read_json(path)
    if not isinstance(data, dict):
        detail["error"] = error or "run manifest is not an object"
        return detail
    digest = _sha256_file(path)
    detail.update(
        {
            "present": True,
            "manifest_sha256": digest,
            "manifest_integrity": (
                "verified"
                if digest is not None and recorded.get("manifest_sha256") == digest
                else ("unknown" if not recorded.get("manifest_sha256") else "mismatch")
            ),
            "status": data.get("status"),
            "backend_id": data.get("backend_id"),
            "solve_kind": data.get("solve_kind"),
            "phasor_convention": data.get("phasor_convention"),
            "frequencies_hz": data.get("frequencies_hz"),
            "excitation_port_ids": data.get("excitation_port_ids"),
            "schema": data.get("schema"),
            "schema_version": data.get("schema_version"),
            "started_at_utc": data.get("started_at_utc"),
            "finished_at_utc": data.get("finished_at_utc"),
            "solver_options": data.get("solver_options"),
            "completion_mask": data.get("completion_mask"),
        }
    )
    engines = data.get("engine_runs")
    if isinstance(engines, list):
        detail["engine_runs"] = [
            {
                "name": _text((run.get("engine") or {}).get("name")) if isinstance(run, dict) else None,
                "backend": _text((run.get("execution") or {}).get("backend"))
                if isinstance(run, dict) and isinstance(run.get("execution"), dict)
                else None,
            }
            for run in engines
            if isinstance(run, dict)
        ]
    meshes = data.get("meshes")
    if isinstance(meshes, list):
        detail["meshes"] = [
            {"id": mesh.get("id"), "name": mesh.get("name"), "purpose": mesh.get("purpose")}
            for mesh in meshes
            if isinstance(mesh, dict)
        ]
    return detail


def _frequencies(run: dict) -> list[float]:
    raw = run.get("frequencies_hz")
    values: list[float] = []
    if isinstance(raw, list):
        for item in raw:
            value = _num(item)
            if value is not None:
                values.append(value)
    return values


def _completion(run: dict) -> tuple[str | None, int, int]:
    freqs = _frequencies(run)
    mask = run.get("completion_mask")
    if isinstance(mask, list) and mask:
        done = sum(1 for item in mask if item)
        total = len(mask)
    elif freqs:
        done = total = len(freqs)
    else:
        return None, 0, 0
    return f"{done}/{total}", done, total


def _classify(payload_ok: bool, payload: dict, run: dict) -> tuple[str, str | None]:
    if not payload_ok:
        return "invalid", None
    # A recorded ``payload.run`` block is not a run: the run manifest must be on disk.
    if run.get("present") and _text(run.get("status")) == "complete":
        return "solved", None
    reason = _refusal_reason(payload, "")
    if reason:
        return "refused", reason
    return "staged", None


def _case_row(
    case: Path,
    experiment: str,
    root: Path,
    declared: dict[str, dict],
) -> tuple[dict, list[dict]]:
    """One row (flat columns + nested run/metadata detail) and its diagnostics."""
    case_key = f"{experiment}/{case.name}"
    diagnostics: list[dict] = []

    manifest_path = case / "manifest.json"
    if manifest_path.is_file():
        manifest, manifest_error = _read_json(manifest_path)
    else:
        manifest, manifest_error = None, "missing manifest.json"
    payload_ok = isinstance(manifest, dict) and isinstance(manifest.get("payload"), dict)
    if payload_ok and isinstance(manifest, dict):
        payload = reparse_payload(manifest.get("payload"))
        created_utc = _text(manifest.get("created_utc"))
        recorded_payload_sha = _text(manifest.get("manifest_payload_sha256"))
        computed_payload_sha = payload_sha256(manifest["payload"])
    else:
        payload = {}
        created_utc = ""
        recorded_payload_sha = ""
        computed_payload_sha = None
    if computed_payload_sha is None:
        manifest_integrity = "unknown"
    elif not recorded_payload_sha:
        manifest_integrity = "unknown"
    elif computed_payload_sha == recorded_payload_sha:
        manifest_integrity = "verified"
    else:
        manifest_integrity = "mismatch"
        diagnostics.append(
            {
                "case_key": case_key,
                "reason": f"manifest payload sha256 mismatch (recorded {recorded_payload_sha[:12]}, "
                f"computed {computed_payload_sha[:12]})",
            }
        )

    run = _run_detail(case, payload)
    status, _ = _classify(payload_ok, payload, run)
    if payload_ok:
        refusal = _refusal_reason(payload, case_key)
        if status == "staged" and refusal:
            status = "refused"
    else:
        refusal = None
    if status == "invalid":
        diagnostics.append(
            {
                "case_key": case_key,
                "reason": manifest_error or "manifest payload missing",
            }
        )

    metadata = _metadata(case, payload) if payload_ok else _empty_metadata()
    frequencies = _frequencies(run)
    completion, done, total = _completion(run)

    result = payload.get("result")
    if isinstance(result, str):
        result, _ = _read_json_str(result)
    result = result if isinstance(result, dict) else {}

    declared_entry = declared.get(case_key) or {}
    declared_bool = bool(declared_entry)
    fidelity = _text(declared_entry.get("fidelity")).strip() or "UNDECLARED"
    motor = _text(declared_entry.get("motor")).strip()
    motor_source = "readiness" if motor else None
    if not motor:
        if isinstance(payload.get("motor_mapping"), dict) or payload.get("motor_role"):
            motor = "real"
            motor_source = "manifest"
        else:
            motor = "UNDECLARED"
    transducer_shape = _text(declared_entry.get("transducer_shape")).strip() or "UNDECLARED"
    gate = _text(declared_entry.get("gate")).strip()
    gate_source = "readiness" if gate else None
    if not gate:
        gate = _text(payload.get("gate")).strip()
        gate_source = "manifest" if gate else None

    project_sha = _text(payload.get("project_sha256"))
    project_file = case / "case.blab.json"
    if project_sha and project_file.is_file():
        project_actual = _sha256_file(project_file)
        project_integrity = (
            "verified" if project_actual == project_sha else ("mismatch" if project_actual else "unknown")
        )
    else:
        project_integrity = "unknown"

    request_sha = _text(payload.get("request_sha256"))
    request_file = _text(payload.get("request_file"))
    request_integrity = "unknown"
    if request_sha and request_file:
        candidates = [case / request_file, case / "run" / request_file]
        existing = next((item for item in candidates if item.is_file()), None)
        if existing is None:
            request_integrity = "file_missing"
        else:
            request_integrity = "verified" if _sha256_file(existing) == request_sha else "mismatch"

    row = {
        "experiment": experiment,
        "case": case.name,
        "case_key": case_key,
        "created_utc": created_utc or None,
        "kind": _text(payload.get("kind")) or None,
        "gate": gate or None,
        "gate_source": gate_source,
        "ref": _text(declared_entry.get("ref")) or None,
        "status": status,
        "solved": status == "solved",
        "n_frequencies": total or None,
        "freq_min_hz": min(frequencies) if frequencies else None,
        "freq_max_hz": max(frequencies) if frequencies else None,
        "backend_id": _text(run.get("backend_id")) or None,
        "solve_kind": _text(run.get("solve_kind")) or None,
        "phasor_convention": _text(run.get("phasor_convention")) or None,
        "completion": completion,
        "authorized_by": _text(_find_first([("payload", payload)], "authorized_by")[0]) or None,
        "fidelity": fidelity,
        "motor": motor,
        "motor_source": motor_source,
        "transducer_shape": transducer_shape,
        "horn_source": _text(declared_entry.get("horn_source")) or None,
        "pair_with": _text(declared_entry.get("pair_with")) or None,
        "project_sha256": project_sha or None,
        "project_integrity": project_integrity,
        "run_manifest_sha256": run.get("manifest_sha256"),
        "run_manifest_integrity": run.get("manifest_integrity"),
        "request_sha256": request_sha or None,
        "request_integrity": request_integrity,
        "manifest_payload_sha256": computed_payload_sha,
        "manifest_integrity": manifest_integrity,
        "box_width_mm": metadata["box_width_mm"],
        "box_height_mm": metadata["box_height_mm"],
        "box_depth_mm": metadata["box_depth_mm"],
        "net_volume_l": metadata["net_volume_l"],
        "net_volume_source": metadata["net_volume_source"],
        "port_area_cm2": metadata["port_area_cm2"],
        "tuning_hz": metadata["tuning_hz"],
        "horn_mesh": metadata["horn_mesh"],
        "horn_mesh_sha256": metadata["horn_mesh_sha256"],
        "horn_offset_mm": metadata["horn_offset_mm"],
        "horn_offset_mm_xyz": metadata["horn_offset_mm_xyz"],
        "clearance_status": metadata["clearance_status"],
        "clearance_min_mm": metadata["clearance_min_mm"],
        "driver_name": metadata["driver_name"],
        "evidence": _text(declared_entry.get("evidence")) or None,
        "notes": _text(declared_entry.get("note")) or None,
        "declared": declared_bool,
        "run_status": _text(run.get("status")) or None,
        "stage_ok": result.get("ok") if isinstance(result.get("ok"), bool) else None,
        "stage_error": _text(result.get("error")) or refusal or None,
        "source_path": _rel(case, root),
    }
    row["run"] = {
        key: value
        for key, value in run.items()
        if key
        in {
            "present",
            "status",
            "schema",
            "schema_version",
            "started_at_utc",
            "finished_at_utc",
            "excitation_port_ids",
            "frequencies_hz",
            "solver_options",
            "engine_runs",
            "meshes",
        }
    }
    row["run"]["completion_mask"] = _completion_mask_summary(run)
    row["metadata"] = {
        "box_source": metadata["box_source"],
        "clearance_source": metadata["clearance_source"],
        "sources": metadata["metadata_sources"],
    }
    return row, diagnostics


def _completion_mask_summary(run: dict) -> dict | None:
    mask = run.get("completion_mask")
    if not isinstance(mask, list) or not mask:
        return None
    return {
        "done": sum(1 for item in mask if item),
        "total": len(mask),
        "complete": all(bool(item) for item in mask),
    }


def _empty_metadata() -> dict:
    return {
        "box_width_mm": None,
        "box_height_mm": None,
        "box_depth_mm": None,
        "box_source": None,
        "net_volume_l": None,
        "net_volume_source": None,
        "port_area_cm2": None,
        "tuning_hz": None,
        "horn_mesh": None,
        "horn_mesh_sha256": None,
        "horn_offset_mm": None,
        "horn_offset_mm_xyz": None,
        "clearance_status": "unknown",
        "clearance_min_mm": None,
        "clearance_source": None,
        "driver_name": None,
        "metadata_sources": [],
    }


# --------------------------------------------------------------------------- readiness registry


def _yaml_scalar(value: object) -> str | None:
    """A YAML scalar as text; dates/datetimes become ISO strings (never a Python object leak)."""
    if value is None:
        return None
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value)
    else:
        isoformat = getattr(value, "isoformat", None)
        text = str(isoformat()) if callable(isoformat) else str(value)
    return text or None


def _case_files(reg_dir: Path, patterns: object) -> list[Path]:
    """The v2 case files a registry declares; only globs confined under ``cases.d/``.

    A ``case_files`` entry may name a narrower glob under ``cases.d/`` but can never point
    outside it: the registry is committed, yet a typo must not send the loader at an arbitrary
    file.  Mirrors ``hornlab_search/gui/data_hw.py::_case_files``.
    """
    chosen = list(patterns or [f"{CASE_FILES_DIR}/*.yaml"])  # type: ignore[arg-type]
    out: list[Path] = []
    for pattern in chosen:
        rel = Path(str(pattern))
        if (
            rel.is_absolute()
            or ".." in rel.parts
            or not rel.parts
            or rel.parts[0] != CASE_FILES_DIR
        ):
            raise ValueError(
                f"case_files entry {pattern!r} must be a relative glob under {CASE_FILES_DIR}/"
            )
        out.extend(sorted(item for item in reg_dir.glob(str(rel)) if item.is_file()))
    return sorted(set(out))


def _v2_cases(reg_dir: Path, data: dict, yaml: Any, errors: list[str]) -> dict[str, dict]:
    """Merge every ``cases.d`` row; drop (and report) keys declared more than once.

    Same policy as the GUI loader (senior review 2026-11-20 §3.1): an ambiguous key is reported
    in ``error`` and left out of the declaration map, never resolved last-wins.
    """
    try:
        files = _case_files(reg_dir, data.get("case_files"))
    except ValueError as exc:
        files = []
        errors.append(str(exc))
    if not files and not errors:
        errors.append(f"cases.d: no case files under {CASE_FILES_DIR}/")

    merged: list[dict] = []
    for case_file in files:
        rel = case_file.relative_to(reg_dir).as_posix()
        try:
            doc = yaml.safe_load(case_file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        rows = doc.get("cases") if isinstance(doc, dict) else doc
        if not isinstance(rows, list):
            errors.append(f"{rel}: expected a 'cases:' list")
            continue
        for row in rows:
            if not isinstance(row, dict) or not _text(row.get("key")).strip():
                errors.append(f"{rel}: case entry without a key")
                continue
            entry = dict(row)
            entry.setdefault("declared_in", rel)
            merged.append(entry)

    counts: dict[str, int] = {}
    for entry in merged:
        key = _text(entry.get("key")).strip()
        counts[key] = counts.get(key, 0) + 1
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        errors.append("duplicate case key(s) across registry files: " + ", ".join(duplicates))

    cases: dict[str, dict] = {}
    for entry in merged:
        key = _text(entry.get("key")).strip()
        if key and counts[key] == 1:
            cases[key] = _clean(entry)
    return cases


def load_readiness(root: Path) -> dict:
    """The declared cases, mapped by ``<experiment>/<case>``.  Declarations only.

    Accepts both registry schemas: v1 declares its rows inline under ``cases``; v2 declares them
    in ``cases.d/*.yaml`` (or the globs a ``case_files`` list names under ``cases.d/``).
    """
    path = root / READINESS_REL
    block: dict = {
        "path": READINESS_REL.as_posix(),
        "found": path.is_file(),
        "schema": None,
        "updated": None,
        "fidelity_note": None,
        "declared_cases": 0,
        "cases": {},
        "error": None,
    }
    if not path.is_file():
        block["error"] = "registry not found"
        return block
    try:
        import yaml  # noqa: PLC0415 - declared project dependency, guarded
    except ImportError:
        block["error"] = "PyYAML not installed; declarations unavailable (all UNDECLARED)"
        return block
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError) as exc:
        block["error"] = f"{type(exc).__name__}: {exc}"
        return block
    if not isinstance(data, dict):
        block["error"] = "registry root is not a mapping"
        return block
    schema = data.get("schema")
    if schema not in REGISTRY_SCHEMAS:
        block["error"] = (
            f"unexpected schema {schema!r} (expected one of {', '.join(REGISTRY_SCHEMAS)})"
        )
        return block

    errors: list[str] = []
    if schema == "hw_readiness_v1":
        # v1 is unchanged: rows are inline and a repeated key keeps its last row.
        cases: dict[str, dict] = {}
        for entry in data.get("cases") or []:
            if not isinstance(entry, dict):
                continue
            key = _text(entry.get("key")).strip()
            if key:
                cases[key] = _clean(entry)
    else:
        cases = _v2_cases(path.parent, data, yaml, errors)

    block.update(
        {
            "schema": schema,
            "updated": _yaml_scalar(data.get("updated")),
            "fidelity_note": _text(data.get("fidelity_note")) or None,
            "declared_cases": len(cases),
            "cases": cases,
        }
    )
    if errors:
        block["error"] = "; ".join(errors).strip("; ")
    elif not cases:
        block["error"] = "registry declares no cases"
    return block


# --------------------------------------------------------------------------- screens


def _screen_counts(raw: object) -> dict:
    source = raw if isinstance(raw, dict) else {}
    return {
        "drivers_loaded": source.get("drivers_loaded"),
        "drivers_rejected": source.get("drivers_rejected"),
        "boxes_considered": source.get("boxes_considered"),
        "boxes_rejected": source.get("boxes_rejected"),
        "candidates_kept": source.get("candidates_kept"),
        "pareto_front_rows": source.get("pareto_front_rows"),
        "shortlist_rows": source.get("shortlist_rows"),
        "placements_considered": source.get("placements_considered"),
        "placements_rejected": source.get("placements_rejected"),
        "xo_hypotheses": source.get("xo_hypotheses"),
        "xo_rejected": source.get("xo_rejected"),
        "bl_panel_fit_rejected": source.get("bl_panel_fit_rejected"),
    }


def _screen_study(path: Path, root: Path) -> tuple[dict | None, str | None]:
    data, error = _read_json(path)
    if not isinstance(data, dict):
        return None, error or "screen file is not an object"
    try:
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        size = stat.st_size
    except OSError:
        mtime = None
        size = None
    catalog = data.get("catalog")
    driver_ids = (
        sorted({_text(row.get("driver_id")) for row in catalog if isinstance(row, dict) and row.get("driver_id")})
        if isinstance(catalog, list)
        else []
    )
    shortlist = data.get("shortlist")
    kept = data.get("kept_rows")
    rejected = data.get("rejected_ledger")
    return (
        {
            "study_id": _text(data.get("study_id")) or None,
            "path": _rel(path, root),
            "created_utc": _text(data.get("created_utc")) or None,
            "mtime_utc": mtime,
            "size_bytes": size,
            "schema": _text(data.get("schema")) or None,
            "system_objective_version": data.get("system_objective_version"),
            "claim": _text(data.get("claim")) or None,
            "input_sha256": _clean(data.get("input_sha256")) if isinstance(data.get("input_sha256"), dict) else None,
            "counts": _screen_counts(data.get("counts")),
            "catalog_driver_ids": driver_ids,
            "catalog_count": len(catalog) if isinstance(catalog, list) else None,
            "envelope": _clean(data.get("envelope")) if isinstance(data.get("envelope"), dict) else None,
            "shortlist_count": len(shortlist) if isinstance(shortlist, list) else None,
            "kept_rows_count": len(kept) if isinstance(kept, list) else None,
            "rejected_ledger_count": len(rejected) if isinstance(rejected, list) else None,
            "shortlist": _clean(shortlist) if isinstance(shortlist, list) else [],
        },
        None,
    )


def _screen_paths(root: Path) -> list[Path]:
    base = root / "system_runs"
    if not base.is_dir():
        return []
    paths: list[Path] = []
    for path in base.rglob("woofer_seed.json"):
        if any(part in SKIP_PARTS for part in path.relative_to(base).parts):
            continue
        paths.append(path)
    screens_dir = base / "screens"
    if screens_dir.is_dir():
        for path in screens_dir.glob("*/*.json"):
            if path.name in {item.name for item in paths}:
                continue
            data, _error = _read_json(path)
            if isinstance(data, dict) and _text(data.get("schema")).startswith("hornlab.system.woofer_seed"):
                paths.append(path)
    return sorted({path.resolve(): path for path in paths}.values(), key=lambda item: item.as_posix())


def scan_screens(root: Path) -> dict:
    diagnostics: list[dict] = []
    studies: list[dict] = []
    for path in _screen_paths(root):
        study, error = _screen_study(path, root)
        if study is None:
            diagnostics.append({"path": _rel(path, root), "reason": error or "unreadable screen"})
            continue
        studies.append(study)
    study_ids = [study["study_id"] for study in studies if study["study_id"]]
    duplicates = sorted({study_id for study_id in study_ids if study_ids.count(study_id) > 1})
    return {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _iso_now(),
        "source": {"root": _rel(root, root), "system_runs": "system_runs"},
        "census": {
            "files": len(studies),
            "unique_study_ids": len(set(study_ids)),
            "duplicate_study_ids": duplicates,
            "shortlist_rows_total": sum(
                (study.get("shortlist_count") or 0) for study in studies
            ),
            "kept_rows_total": sum((study.get("kept_rows_count") or 0) for study in studies),
        },
        "diagnostics": diagnostics,
        "studies": studies,
    }


# --------------------------------------------------------------------------- document


def scan_cases(root: Path, readiness: dict) -> tuple[list[dict], dict, list[dict]]:
    base = root / "system_runs" / "system"
    declared: dict[str, dict] = readiness.get("cases") or {}
    rows: list[dict] = []
    diagnostics: list[dict] = []
    scanned = 0
    present = base.is_dir()
    if not present:
        diagnostics.append({"case_key": None, "reason": "system_runs/system is missing"})

    for experiment_dir in (
        sorted((item for item in base.iterdir() if item.is_dir()), key=lambda item: item.name)
        if present
        else []
    ):
        if experiment_dir.name in SKIP_PARTS or experiment_dir.name.startswith("_"):
            continue
        try:
            entries = sorted((item for item in experiment_dir.iterdir() if item.is_dir()), key=lambda item: item.name)
        except OSError as exc:
            diagnostics.append({"case_key": experiment_dir.name, "reason": f"unreadable experiment dir: {exc}"})
            continue
        for case_dir in entries:
            if not CASE_DIR_RE.match(case_dir.name):
                continue
            scanned += 1
            try:
                row, case_diagnostics = _case_row(case_dir, experiment_dir.name, root, declared)
            except Exception as exc:  # noqa: BLE001 - a malformed case must never stop the export
                diagnostics.append(
                    {
                        "case_key": f"{experiment_dir.name}/{case_dir.name}",
                        "reason": f"unexpected {type(exc).__name__}: {exc}",
                    }
                )
                continue
            rows.append(row)
            diagnostics.extend(case_diagnostics)

    rows.sort(key=lambda row: (row["experiment"], row["case"]))
    on_disk = {row["case_key"] for row in rows}
    for key in sorted(declared):
        if key not in on_disk:
            diagnostics.append({"case_key": key, "reason": "declared in readiness.yaml but not on disk"})

    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    by_fidelity: dict[str, int] = {}
    for row in rows:
        by_fidelity[row["fidelity"]] = by_fidelity.get(row["fidelity"], 0) + 1
    by_clearance: dict[str, int] = {}
    for row in rows:
        by_clearance[row["clearance_status"]] = by_clearance.get(row["clearance_status"], 0) + 1

    census = {
        "scanned": scanned,
        "included": len(rows),
        "by_status": dict(sorted(by_status.items())),
        "by_fidelity": dict(sorted(by_fidelity.items())),
        "by_clearance": dict(sorted(by_clearance.items())),
        "experiments": len({row["experiment"] for row in rows}),
        "solved": sum(1 for row in rows if row["solved"]),
        "declared": sum(1 for row in rows if row["declared"]),
        "declared_missing_on_disk": sum(1 for key in declared if key not in on_disk),
        "on_disk_not_declared": sum(1 for row in rows if not row["declared"]),
        "manifest_integrity": _count_field(rows, "manifest_integrity"),
        "run_manifest_integrity": _count_field(rows, "run_manifest_integrity"),
        "project_integrity": _count_field(rows, "project_integrity"),
        "request_integrity": _count_field(rows, "request_integrity"),
        "diagnostics": len(diagnostics),
    }
    return rows, census, diagnostics


def _count_field(rows: list[dict], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def build_document(root: Path, *, include_screens: bool = True) -> tuple[dict, dict | None]:
    """Build the cases document (and the screens document when screens are requested)."""
    readiness = load_readiness(root)
    rows, census, diagnostics = scan_cases(root, readiness)
    if readiness.get("error"):
        diagnostics.append({"case_key": None, "reason": f"readiness: {readiness['error']}"})
    census["diagnostics"] = len(diagnostics)
    document = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _iso_now(),
        "source": {
            "root": ".",
            "system_runs": "system_runs",
            "readiness": readiness["path"],
            "tool_path": _rel(Path(__file__), REPO_ROOT),
            "note": "paths are repo-relative; system_runs/ is the git-ignored system store",
        },
        "readiness": {key: value for key, value in readiness.items() if key != "cases"},
        "census": census,
        "diagnostics": diagnostics,
        "cases": rows,
    }
    screens = scan_screens(root) if include_screens else None
    return document, screens


# --------------------------------------------------------------------------- writers


def _write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def _remove_stale_artifact(path: Path) -> None:
    """Remove a previous *generated* bundle file (never a hand-written one)."""
    if not path.is_file():
        return
    data, _error = _read_json(path)
    if isinstance(data, dict) and data.get("tool") == TOOL and "census" in data:
        try:
            path.unlink()
        except OSError:
            pass


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CASE_CSV_FIELDS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in CASE_CSV_FIELDS})
    os.replace(tmp, path)


def write_json(path: Path, document: dict, *, pretty: bool) -> None:
    if pretty:
        text = json.dumps(_clean(document), indent=2, sort_keys=False, allow_nan=False)
    else:
        text = json.dumps(_clean(document), sort_keys=False, separators=(",", ":"), allow_nan=False)
    _write_text_lf(path, text + "\n")


def run(
    *,
    root: Path,
    out_dir: Path,
    write_csv_file: bool = True,
    write_screens: bool = True,
    pretty: bool = False,
) -> tuple[dict, dict | None, list[str], bool]:
    """Write the bundle and return ``(document, screens, written, ok)``.

    ``ok`` is False when a diagnostic exists (invalid case, integrity mismatch, unusable
    registry); ``main`` maps that to exit code 1 only under ``--strict``.
    """
    document, screens = build_document(root, include_screens=write_screens)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    if write_csv_file:
        write_csv(out_dir / CASE_NAMES["csv"], document["cases"])
        written.append(CASE_NAMES["csv"])
    write_json(out_dir / CASE_NAMES["json"], document, pretty=pretty)
    written.append(CASE_NAMES["json"])
    if write_screens and screens is not None:
        write_json(out_dir / CASE_NAMES["screens"], screens, pretty=pretty)
        written.append(CASE_NAMES["screens"])
    elif not write_screens:
        # Do not leave a previous run's screens bundle lying next to a cases-only export: it would
        # describe a tree this run did not read.  Only a file this tool wrote is removed.
        _remove_stale_artifact(out_dir / CASE_NAMES["screens"])

    failures = [item for item in document["diagnostics"]]
    if any(row.get("manifest_integrity") == "mismatch" for row in document["cases"]):
        failures.append({"case_key": None, "reason": "one or more manifest payload hash mismatches"})
    ok = not failures
    return document, screens, written, ok


# --------------------------------------------------------------------------- CLI


def _summary_lines(document: dict, screens: dict | None, written: list[str], out_dir: Path) -> list[str]:
    census = document["census"]
    by_status = census.get("by_status", {})
    lines = [
        "system_cases: HORN + VENTED-WOOFER system cases and screens",
        f"  scanned           : {census.get('scanned', 0)} timestamped case dirs",
        f"  included          : {census.get('included', 0)} rows",
        "  by status         : "
        + ", ".join(f"{key} {value}" for key, value in by_status.items()),
        f"  declared (readiness): {census.get('declared', 0)} "
        f"(missing on disk {census.get('declared_missing_on_disk', 0)})",
        f"  fidelity          : "
        + ", ".join(f"{key} {value}" for key, value in census.get("by_fidelity", {}).items()),
        f"  clearance         : "
        + ", ".join(f"{key} {value}" for key, value in census.get("by_clearance", {}).items()),
        f"  integrity         : manifest {census.get('manifest_integrity', {})}",
        f"  diagnostics       : {len(document.get('diagnostics') or [])}",
    ]
    if screens is not None:
        lines.append(
            f"  screens           : {screens['census']['files']} files, "
            f"{screens['census']['unique_study_ids']} unique study ids, "
            f"{screens['census']['shortlist_rows_total']} shortlist rows"
        )
    else:
        lines.append("  screens           : not written")
    lines.append(f"  output            : {out_dir}")
    lines.append("  files written     : " + (", ".join(written) if written else "none"))
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="system_cases.py",
        description=(
            "Export the HORN + VENTED-WOOFER system case store and woofer screens to a portable "
            "CSV/JSON bundle (read-only over system_runs/)."
        ),
    )
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument(
        "--out",
        default="docs/system_data",
        help="output directory, relative to --root (default: docs/system_data)",
    )
    parser.add_argument("--no-csv", action="store_true", help="do not write system_cases.csv")
    parser.add_argument("--no-screens", action="store_true", help="do not scan/write woofer screens")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON files")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any diagnostic exists (invalid case, hash mismatch, unusable registry)",
    )
    parser.add_argument("--quiet", action="store_true", help="do not print the summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_absolute():
        root = (REPO_ROOT / root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    document, screens, written, ok = run(
        root=root,
        out_dir=out_dir,
        write_csv_file=not args.no_csv,
        write_screens=not args.no_screens,
        pretty=args.pretty,
    )
    if not args.quiet:
        for line in _summary_lines(document, None if args.no_screens else screens, written, out_dir):
            print(line)
        for item in document.get("diagnostics") or []:
            print(f"  diagnostic        : {item.get('case_key')}: {item.get('reason')}")
    if args.strict and not ok:
        print("system_cases: strict mode: diagnostics present", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
