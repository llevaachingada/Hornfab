"""One reader for every system case kind (contract ``01_CONTRACTS.md`` section 2).

This is a port of the status rules, metadata-walk order and integrity checks of
``tools/data/system_cases.py`` into the typed :mod:`case_schema` model.  The tool may keep its
own copy for the export bundle; this module must never import the tool, Boundary Lab, the
solver or the GUI.

Guarantees:

* ``read_case`` never raises on bad data: unreadable/missing/malformed manifests return
  ``status="invalid"`` with diagnostics; malformed side-cars only add diagnostics.
* every path that is split or made relative goes through :mod:`hornlab_search.system.paths`,
  so a Windows manifest reads identically on Linux.
* facts come from the case directory; declarations come only from ``readiness.yaml``.  A case
  missing from the registry is ``UNDECLARED``; nothing is inferred.
* case-level refusals only: ``spec.geometry.refusals`` field ledgers (``GEOMETRY_FIELD_UNAVAILABLE``)
  and a generic ``BL_CAPABILITY_OK`` status are **not** refusals.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from hornlab_search.system import paths
from hornlab_search.system.case_schema import (
    CaseHeader,
    ClearanceBlock,
    Declaration,
    GeometryBlock,
    SolveBlock,
    StageBlock,
    SystemCase,
    UNDECLARED,
)
from hornlab_search.system.contracts import canonical_json

__all__ = ["CASE_DIR_RE", "iter_cases", "load_readiness", "read_case"]

READINESS_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")

#: A case directory is a UTC timestamp prefix (``20261118T225108Z-...``).
CASE_DIR_RE = re.compile(r"^\d{8}T\d{6}Z")

#: Experiment/case path parts that are not study records.
SKIP_PARTS = frozenset({"_fixtures", "__pycache__", ".git"})

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


def _read_json(path: Path) -> tuple[Any, str | None]:
    """``(data, error)``; never raises."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _read_json_str(text: str) -> tuple[Any, str | None]:
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        return None


def _store_rel(path: Path, store_root: Path) -> str:
    """Store-relative POSIX path (the marker/root logic lives in :mod:`paths`)."""
    relative = paths.to_store_relative(str(path), [str(store_root)])
    return relative if relative is not None else Path(path).name


# --------------------------------------------------------------------------- manifest hashing


def _reparse_payload(payload: object) -> dict:
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


def _payload_sha256(payload: dict) -> str:
    return _sha256_bytes(canonical_json(_reparse_payload(payload)).encode("utf-8"))


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
        for _path, node in _walk_dicts(doc):
            for key in keys:
                if key in node:
                    value = node[key]
                    if not isinstance(value, (dict, list)):
                        return value, label
    return None, None


def _find_path_value(docs: list[tuple[str, Any]], *suffixes: tuple[str, ...]) -> Any:
    """First scalar at a key path ending with one of ``suffixes``."""
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
        for _path, node in _walk_dicts(doc):
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


def _clearance_block(record: dict | None, label: str | None) -> ClearanceBlock | None:
    """A recorded clearance verdict as a contract block (never inferred)."""
    if record is None:
        return None
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
    elif raw in {"UNPROVEN", "NOT_PROVEN"}:
        status = "unproven"
    elif raw in {"NOT_CHECKED", "NOT-RECORDED", "UNKNOWN"}:
        status = "not_recorded"
    elif record.get("ok") is True:
        status = "pass"
    elif record.get("ok") is False:
        status = "violation"
    else:
        status = "not_recorded"
    return ClearanceBlock(status=status, min_gap_mm=minimum, source=label or "")


def _metadata_documents(case: Path, payload: dict) -> list[tuple[str, Any]]:
    """Ordered metadata sources: the four named files first, then the case's own side-cars.

    A staged case has no ``run/`` tree, so the adapter/stage reports are the only place the box,
    horn and driver declarations exist.  Every source is named so a null can be traced.
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
        data, _error = _read_json(case / rel)
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


def _extract_metadata(case: Path, payload: dict) -> tuple[dict, list[str]]:
    """Defensive per-field extraction; absent keys become ``None``."""
    docs = _metadata_documents(case, payload)
    box, _box_source = _find_box_source(docs)
    horn, _horn_source = _find_horn(docs)
    clearance_record, clearance_source = _find_clearance_record(docs)

    width = height = depth = None
    if box is not None:
        width = _mm_from_m(box.get("width_m"))
        height = _mm_from_m(box.get("height_m"))
        depth = _mm_from_m(box.get("depth_m"))

    port_area_cm2 = None
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
    horn_offset_xyz = None
    if horn is not None:
        value = _text(horn.get("mesh_sha256"))
        if value:
            horn_mesh_sha256 = value
        for key in ("mesh_path", "mesh_file"):
            value = _text(horn.get(key))
            if value:
                # Split on both separators: a Windows path is not split by pathlib on Linux.
                horn_mesh = paths.leaf_dir_name(value) or (paths.split_any(value)[-1] if paths.split_any(value) else None)
                break
        if horn_mesh is None:
            horn_mesh = _text(horn.get("mesh_name")) or _text(horn.get("name")) or None
        raw_translation = horn.get("translation_mm")
        if isinstance(raw_translation, (list, tuple)):
            components = [_num(item) for item in raw_translation]
            if components and all(item is not None for item in components):
                values = [float(item) for item in components if item is not None]
                horn_offset_xyz = tuple(round(item, 3) for item in values)

    tuning_hz = _num(_find_first(docs, "tuning_hz")[0])

    return (
        {
            "box_mm": (width, height, depth),
            "net_volume_l": net_volume_l,
            "net_volume_source": net_volume_source,
            "port_area_cm2": port_area_cm2,
            "tuning_hz": None if tuning_hz is None else round(tuning_hz, 3),
            "horn_mesh": horn_mesh,
            "horn_mesh_sha256": horn_mesh_sha256,
            "horn_offset_mm_xyz": horn_offset_xyz,
            "driver_name": _driver_name(docs),
            "clearance": _clearance_block(clearance_record, clearance_source),
        },
        [label for label, _doc in docs],
    )


# --------------------------------------------------------------------------- run detail


def _run_detail(case: Path, payload: dict) -> dict:
    """``run/manifest.json`` facts plus the recorded run block from ``payload.run``."""
    recorded_raw = payload.get("run")
    recorded = _reparse_payload({"run": recorded_raw})["run"] if recorded_raw else None
    if not isinstance(recorded, dict):
        recorded = {}

    detail: dict = {
        "present": False,
        "manifest_sha256": None,
        "manifest_integrity": "unknown",
        "status": recorded.get("status"),
        "backend_id": recorded.get("backend_id"),
        "solve_kind": recorded.get("solve_kind"),
        "frequencies_hz": recorded.get("frequencies_hz"),
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
    recorded_sha = _text(recorded.get("manifest_sha256"))
    detail.update(
        {
            "present": True,
            "manifest_sha256": digest,
            "manifest_integrity": (
                "verified"
                if digest is not None and recorded_sha == digest
                else ("unknown" if not recorded_sha else "mismatch")
            ),
            "status": data.get("status"),
            "backend_id": data.get("backend_id"),
            "solve_kind": data.get("solve_kind"),
            "frequencies_hz": data.get("frequencies_hz"),
            "completion_mask": data.get("completion_mask"),
        }
    )
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


def _completion(run: dict) -> tuple[int, int]:
    freqs = _frequencies(run)
    mask = run.get("completion_mask")
    if isinstance(mask, list) and mask:
        return sum(1 for item in mask if item), len(mask)
    if freqs:
        return len(freqs), len(freqs)
    return 0, 0


# --------------------------------------------------------------------------- refusals


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


def _refusal_reason(payload: dict) -> str | None:
    """A case-level refusal reason, else ``None`` (field ledgers and BL_CAPABILITY_OK excluded)."""
    result = payload.get("result")
    if isinstance(result, str):
        result, _error = _read_json_str(result)
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


def _refusal_tokens(payload: dict) -> tuple[str, ...]:
    """Stable tokens found in payload string values; ``REFUSED`` for ``refused: true``."""
    tokens: list[str] = []
    for match in REFUSAL_TOKEN_RE.finditer(_flatten_strings(payload)):
        token = match.group(0)
        if token not in tokens:
            tokens.append(token)
    if payload.get("refused") is True and "REFUSED" not in tokens:
        tokens.append("REFUSED")
    return tuple(tokens)


# --------------------------------------------------------------------------- readiness


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


def load_readiness(repo_root: Path) -> Mapping | None:
    """Declared cases from ``docs/research/system_woofer_2026-11-18/readiness.yaml``.

    Returns ``{case_key: entry}`` or ``None`` when the registry is absent, unreadable or has an
    unexpected schema.  Declarations only: status facts never come from here.
    """
    path = Path(repo_root) / READINESS_REL
    if not path.is_file():
        return None
    try:
        import yaml  # noqa: PLC0415 - declared project dependency, guarded
    except ImportError:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != "hw_readiness_v1":
        return None
    declared: dict[str, dict] = {}
    for entry in data.get("cases") or []:
        if not isinstance(entry, dict):
            continue
        key = _text(entry.get("key")).strip()
        if key:
            declared[key] = _clean(entry)
    return declared


def _declared_cases(readiness: Mapping | None) -> Mapping:
    if not isinstance(readiness, Mapping):
        return {}
    nested = readiness.get("cases")
    if isinstance(nested, Mapping):
        return nested
    if isinstance(nested, (list, tuple)):
        built: dict[str, Mapping] = {}
        for entry in nested:
            if isinstance(entry, Mapping):
                key = _text(entry.get("key")).strip()
                if key:
                    built[key] = entry
        return built
    return readiness


def _declaration_entry(declared: Mapping, case_key: str) -> Mapping:
    entry = declared.get(case_key)
    return entry if isinstance(entry, Mapping) else {}


# --------------------------------------------------------------------------- case reader


def _invalid_case(
    case_dir: Path,
    store_root: Path,
    readiness: Mapping | None,
    reason: str,
) -> SystemCase:
    experiment = Path(case_dir).parent.name
    case = Path(case_dir).name
    return SystemCase(
        header=CaseHeader(
            case_key=f"{experiment}/{case}",
            experiment=experiment,
            case=case,
            kind=None,
            created_utc=None,
            status="invalid",
            status_reason="UNPARSEABLE",
            manifest_integrity="unknown",
            source_path=_store_rel(Path(case_dir), Path(store_root)),
        ),
        declaration=_declaration({}, {}, case_key=f"{experiment}/{case}"),
        stage=None,
        solve=None,
        geometry=None,
        refusals=(),
        diagnostics=(reason,),
        sources=(),
    )


def _declaration(declared: Mapping, payload: dict, *, case_key: str) -> Declaration:
    entry = _declaration_entry(declared, case_key)
    fidelity = _text(entry.get("fidelity")).strip() or UNDECLARED
    motor = _text(entry.get("motor")).strip()
    motor_source: str | None = "readiness" if motor else None
    if not motor:
        if isinstance(payload.get("motor_mapping"), dict) or payload.get("motor_role"):
            motor = "real"
            motor_source = "manifest"
        else:
            motor = UNDECLARED
    gate = _text(entry.get("gate")).strip()
    if not gate:
        gate = _text(payload.get("gate")).strip()
    return Declaration(
        declared=bool(entry),
        fidelity=fidelity,
        motor=motor,
        motor_source=motor_source,
        transducer_shape=_text(entry.get("transducer_shape")).strip() or UNDECLARED,
        gate=gate or None,
        ref=_text(entry.get("ref")) or None,
        evidence=_text(entry.get("evidence")) or None,
        horn_source=_text(entry.get("horn_source")) or None,
        pair_with=_text(entry.get("pair_with")) or None,
    )


def _read_case(case_dir: Path, store_root: Path, readiness: Mapping | None) -> SystemCase:
    case_dir = Path(case_dir)
    store_root = Path(store_root)
    experiment = case_dir.parent.name
    case = case_dir.name
    case_key = f"{experiment}/{case}"
    declared = _declared_cases(readiness)
    diagnostics: list[str] = []

    manifest_path = case_dir / "manifest.json"
    manifest_present = manifest_path.is_file()
    if manifest_present:
        manifest, manifest_error = _read_json(manifest_path)
    else:
        manifest, manifest_error = None, "missing manifest.json"
    payload_ok = isinstance(manifest, dict) and isinstance(manifest.get("payload"), dict)

    if payload_ok:
        payload = _reparse_payload(manifest.get("payload"))
        created_utc = _text(manifest.get("created_utc")) or None
        recorded_payload_sha = _text(manifest.get("manifest_payload_sha256"))
        computed_payload_sha: str | None = _payload_sha256(manifest["payload"])
    else:
        payload = {}
        created_utc = None
        recorded_payload_sha = ""
        computed_payload_sha = None

    if computed_payload_sha is None or not recorded_payload_sha:
        manifest_integrity = "unknown"
    elif computed_payload_sha == recorded_payload_sha:
        manifest_integrity = "verified"
    else:
        manifest_integrity = "mismatch"
        diagnostics.append(
            "manifest payload sha256 mismatch "
            f"(recorded {recorded_payload_sha[:12]}, computed {computed_payload_sha[:12]})"
        )

    run = _run_detail(case_dir, payload)
    refusal = _refusal_reason(payload) if payload_ok else None

    if not payload_ok:
        status = "invalid"
        status_reason = "NO_MANIFEST" if not manifest_present else "UNPARSEABLE"
        diagnostics.append(manifest_error or "manifest payload missing")
    elif run.get("present") and _text(run.get("status")) == "complete":
        status = "solved"
        status_reason = "RUN_COMPLETE"
    elif refusal:
        status = "refused"
        status_reason = "CASE_REFUSED"
    else:
        status = "staged"
        status_reason = "MANIFEST_ONLY"

    metadata: dict | None = None
    document_labels: list[str] = []
    if payload_ok:
        metadata, document_labels = _extract_metadata(case_dir, payload)

    result = payload.get("result")
    if isinstance(result, str):
        result, _ = _read_json_str(result)
    result = result if isinstance(result, dict) else {}

    stage = None
    if payload_ok:
        project = case_dir / "case.blab.json"
        stage = StageBlock(
            ok=result.get("ok") if isinstance(result.get("ok"), bool) else None,
            error=_text(result.get("error")) or refusal or None,
            project_rel=_store_rel(project, store_root) if project.is_file() else None,
            clearance=metadata["clearance"] if metadata else None,
        )

    solve = None
    if payload_ok:
        frequencies = _frequencies(run)
        done, total = _completion(run)
        authorized_by = _text(_find_first([("payload", payload)], "authorized_by")[0]) or None
        solve = SolveBlock(
            run_status=_text(run.get("status")) or None,
            n_frequencies=total or None,
            freq_min_hz=min(frequencies) if frequencies else None,
            freq_max_hz=max(frequencies) if frequencies else None,
            backend_id=_text(run.get("backend_id")) or None,
            solve_kind=_text(run.get("solve_kind")) or None,
            completion_done=done if total else None,
            completion_total=total or None,
            authorized_by=authorized_by,
            run_manifest_integrity=_text(run.get("manifest_integrity")) or "unknown",
        )

    geometry = None
    if metadata is not None:
        geometry = GeometryBlock(
            box_mm=metadata["box_mm"],
            net_volume_l=metadata["net_volume_l"],
            net_volume_source=metadata["net_volume_source"],
            port_area_cm2=metadata["port_area_cm2"],
            tuning_hz=metadata["tuning_hz"],
            horn_mesh=metadata["horn_mesh"],
            horn_mesh_sha256=metadata["horn_mesh_sha256"],
            horn_offset_mm_xyz=metadata["horn_offset_mm_xyz"],
            driver_name=metadata["driver_name"],
        )

    tokens = _refusal_tokens(payload) if payload_ok else ()
    if status == "refused" and not tokens:
        tokens = ("CASE_REFUSED",)

    sources: list[str] = []
    if manifest_present:
        sources.append(_store_rel(manifest_path, store_root))
    for label in document_labels:
        if label == "manifest.payload":
            continue
        rel = _store_rel(case_dir / label, store_root)
        if rel not in sources:
            sources.append(rel)

    return SystemCase(
        header=CaseHeader(
            case_key=case_key,
            experiment=experiment,
            case=case,
            kind=_text(payload.get("kind")) or None,
            created_utc=created_utc,
            status=status,
            status_reason=status_reason,
            manifest_integrity=manifest_integrity,
            source_path=_store_rel(case_dir, store_root),
        ),
        declaration=_declaration(declared, payload, case_key=case_key),
        stage=stage,
        solve=solve,
        geometry=geometry,
        refusals=tokens,
        diagnostics=tuple(diagnostics),
        sources=tuple(sources),
    )


def read_case(case_dir: Path, *, store_root: Path, readiness: Mapping | None = None) -> SystemCase:
    """Read one case directory; never raises on bad data (returns ``status="invalid"``)."""
    try:
        return _read_case(Path(case_dir), Path(store_root), readiness)
    except Exception as exc:  # noqa: BLE001 - a malformed case must never stop the reader
        return _invalid_case(
            Path(case_dir),
            Path(store_root),
            readiness,
            f"unexpected {type(exc).__name__}: {exc}",
        )


def iter_cases(store_root: Path, *, readiness: Mapping | None = None) -> Iterator[SystemCase]:
    """Walk ``<store_root>/system/<experiment>/<CASE_DIR_RE>``, sorted by (experiment, case)."""
    base = Path(store_root) / "system"
    if not base.is_dir():
        return
    try:
        experiments = sorted((item for item in base.iterdir() if item.is_dir()), key=lambda item: item.name)
    except OSError:
        return
    for experiment_dir in experiments:
        if experiment_dir.name in SKIP_PARTS or experiment_dir.name.startswith("_"):
            continue
        try:
            entries = sorted(
                (item for item in experiment_dir.iterdir() if item.is_dir()), key=lambda item: item.name
            )
        except OSError:
            continue
        for case_dir in entries:
            if not CASE_DIR_RE.match(case_dir.name):
                continue
            yield read_case(case_dir, store_root=store_root, readiness=readiness)
