"""Horn + woofer GUI - P6 Boundary Lab action backend (stage / validate / solve).

This module is the single validation point for the three ``hw-*`` Boundary Lab job kinds.
``jobs.build_argv`` calls :func:`stage_argv`, :func:`validate_argv` and :func:`solve_argv`, so the
ranges, enums and allow-lists live here only (never duplicated in JS or in ``jobs.py``).

What comes from where (never invented):

* **Horn meshes** - only the newest closed full-domain cases recorded under
  ``<store>/system/ref_case/horn_full/*/mesh.msh``.  A caller's path is resolved and then checked
  against that allow-list; a path anywhere else is refused before any read.  Physical groups are
  read from the mesh file itself (read-only, ``meshio``), never from a user-supplied string.
* **Stage defaults** - the committed example spec ``examples/systems/two_way_80x50_700_research.yaml``
  parsed by the frozen :func:`hornlab_search.system.contracts.parse_system_spec_dict`.  The example
  carries search *ranges*, so ``--overrides`` stays empty until a concrete shortlisted box is chosen;
  Boundary Lab's provider ``default_source`` is the fallback, exactly as the CLI's ``prepare`` uses it.
* **Solve presets** - frequency grids and CPU-time estimates are read from the recorded run
  manifests under ``<store>/system/*/*/run/manifest.json``.  A preset with no recorded run says
  ``estimate unavailable``; no time is fabricated.  The low-band preset (R3) names its documented
  band and log spacing but still reports an unavailable estimate until an LF run exists.
* **Solve authorization** - owner decision 6 is read from the readiness registry.  The environment
  flag ``HORNLAB_GUI_ALLOW_BL_SOLVE=1`` alone is never enough: without a recorded decision the
  launch is refused by name (gate D is unanswered).

No solver, no Boundary Lab import, no GPU.  Everything here is CPU-only argv assembly and
read-only file inspection.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from hornlab_search.system import contracts as C
from hornlab_search.system.boundarylab.clearance import DEFAULT_MIN_GAP_M

__all__ = [
    "DECISION_ID",
    "DECISION_REASON",
    "DEFAULT_SPEC_REL",
    "ENV_ALLOW_SOLVE",
    "HORN_SUBDIR",
    "SOLVE_PRESETS",
    "StageArgError",
    "authorization_state",
    "solve_argv",
    "solve_presets",
    "solve_request",
    "stage_argv",
    "stage_options",
    "stage_preview",
    "validate_argv",
    "write_solve_request",
]

#: Same one-component shape every GUI path/key uses.
_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
#: A Boundary Lab vented-source override key (BL itself validates the keyset and ranges).
_OVERRIDE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: The only folder the GUI may stage a horn from (store-relative).
HORN_SUBDIR = Path("system") / "ref_case" / "horn_full"
#: Committed example spec that supplies the stage-dialog defaults.
DEFAULT_SPEC_REL = Path("examples/systems/two_way_80x50_700_research.yaml")
#: Readiness registry that records the owner decisions (decision 6 gates GUI solves).
READINESS_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")

#: Exposed translation range for the horn's z offset (x/y stay fixed at 0).
TRANSLATION_Z_MIN = -100.0
TRANSLATION_Z_MAX = 200.0
#: A clearance value is not a stage choice: the CLI stage path enforces the R16 1 mm minimum.
#: Kept in stage_options as a note only (senior review 2026-11-20 F5).
#: Allowed solve presets (the GUI shows exactly these; no free-form grid).
SOLVE_PRESETS = ("smoke3", "wide25", "lowband12")

#: Gate D: the flag is only half the requirement.
ENV_ALLOW_SOLVE = "HORNLAB_GUI_ALLOW_BL_SOLVE"
DECISION_ID = 6
DECISION_REASON = "needs owner approval for GUI-started Boundary Lab solves (decision 6)"

#: Preset metadata; the frequency lists themselves are read from the recorded runs.
_PRESET_META: dict[str, dict[str, Any]] = {
    "smoke3": {"label": "Smoke 3 freqs", "band_hz": [250.0, 1100.0],
               "recorded_count": 3},
    "wide25": {"label": "Wide 25 freqs 200-2500 Hz", "band_hz": [200.0, 2500.0],
               "recorded_count": 25},
    "lowband12": {"label": "Low band 12 freqs 20-200 Hz (R3)", "band_hz": [20.0, 200.0],
                  "recorded_count": 12},
}

#: The two independent excitations the reference case records (see reference.py).
_REFERENCE_PORTS = ("vented/voltage", "excitation:horn")


class StageArgError(ValueError):
    """A Boundary Lab action request that must be refused; jobs.py re-raises it as JobError."""


# --------------------------------------------------------------------------- small helpers


def _root(root: str | Path) -> Path:
    return Path(root)


def _store(root: str | Path, store: str | Path | None) -> Path:
    """The literal store path (not resolved): the canonical ``system_runs`` may be a junction."""
    if store is not None:
        return Path(store)
    return _root(root) / "system_runs"


def _store_label(root: str | Path, store: str | Path) -> str:
    """Repo-relative store path when literal-contained, else the absolute store path."""
    st = Path(store)
    try:
        return st.relative_to(Path(root)).as_posix()
    except ValueError:
        return st.as_posix()


def _path_label(root: str | Path, store: str | Path, parts: tuple[str, ...]) -> str:
    """The argv path for a store-relative item, kept readable when the store is in the repo."""
    full = Path(store).joinpath(*parts)
    try:
        return full.relative_to(Path(root)).as_posix()
    except ValueError:
        return full.as_posix()


def _default_experiment_id() -> str:
    return "bl_gui_" + _dt.date.today().strftime("%Y%m%d")


def _float_arg(value: Any, lo: float, hi: float, field: str, default: float | None = 0.0) -> float:
    if value in (None, ""):
        if default is None:
            raise StageArgError(f"{field}: a value is required")
        return float(default)
    if isinstance(value, bool):
        raise StageArgError(f"{field} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise StageArgError(f"{field} must be a number") from None
    if not math.isfinite(number) or not lo <= number <= hi:
        raise StageArgError(f"{field} must be in [{lo}, {hi}]")
    return number


def _key_arg(value: Any, field: str, default: str) -> str:
    text = str(default) if value in (None, "") else str(value).strip()
    if not _KEY_PART.fullmatch(text) or ".." in text:
        raise StageArgError(
            f"{field}: must match ^[A-Za-z0-9][A-Za-z0-9_.-]{{0,120}}$ and contain no '..'")
    return text


# --------------------------------------------------------------------------- horn meshes


def _mesh_summary(path: Path) -> tuple[list[str], int]:
    """(sorted 2D physical-group names, triangle count) read from the mesh file itself."""
    import meshio

    mesh = meshio.read(path)
    # gmsh field_data entries are (tag, dimension); the stage runner assigns boundaries only
    # from 2D physical groups, so list exactly those (never a 1D/3D label).
    groups: list[str] = []
    for key, value in (mesh.field_data or {}).items():
        try:
            dimension = int(value[1])
        except (TypeError, IndexError, ValueError):
            dimension = 2
        if dimension == 2:
            groups.append(str(key))
    triangles = sum(int(len(cell.data)) for cell in mesh.cells if cell.type == "triangle")
    return sorted(groups), triangles


def _allowed_base(store: str | Path) -> Path:
    return (Path(store) / HORN_SUBDIR).resolve()


def _resolve_horn_mesh(root: str | Path, store: str | Path, value: Any) -> tuple[Path, Path]:
    """Resolve an allow-listed horn mesh; return (absolute path, store-relative path)."""
    if not isinstance(value, str) or not value.strip():
        raise StageArgError("horn_mesh: an allow-listed full-domain horn mesh is required")
    raw = Path(value.strip())
    candidates = [raw] if raw.is_absolute() else [Path(store) / raw, Path(root) / raw]
    base = _allowed_base(store)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.is_file() or resolved.name != "mesh.msh":
            continue
        if base not in resolved.parents or resolved.parent.parent != base:
            continue
        rel = resolved.relative_to(base)
        return resolved, HORN_SUBDIR / rel
    raise StageArgError(
        f"horn_mesh: not an allow-listed mesh under "
        f"{_store_label(root, Path(store) / HORN_SUBDIR)}/*/mesh.msh: {value!r}")


def _resolve_case(root: str | Path, store: str | Path, value: Any) -> tuple[Path, Path]:
    """Resolve an existing ``<experiment>/<case>`` inside the system store."""
    parts = str(value).strip("/").split("/") if value is not None else []
    if (len(parts) != 2 or not all(_KEY_PART.fullmatch(p) and ".." not in p for p in parts)):
        raise StageArgError("case: expected <experiment>/<case> with safe name components")
    base = (Path(store) / "system").resolve()
    case = (base / parts[0] / parts[1]).resolve()
    if base not in case.parents or not case.is_dir():
        raise StageArgError(f"case: no such case inside the system store: {value!r}")
    return case, Path("system") / parts[0] / parts[1]


# --------------------------------------------------------------------------- stage options


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _spec_defaults(root: str | Path) -> dict[str, Any]:
    """Stage defaults from the committed example spec, parsed by the frozen contract parser."""
    repo = _root(root)
    path = repo / DEFAULT_SPEC_REL
    if not path.is_file():
        return {
            "source": DEFAULT_SPEC_REL.as_posix(),
            "box": None,
            "assembly": None,
            "box_overrides": {},
            "note": f"committed example spec absent: {DEFAULT_SPEC_REL.as_posix()}",
        }
    try:
        spec = C.parse_system_spec_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except Exception as exc:  # noqa: BLE001 - the workbook shows the parser's own message
        return {
            "source": DEFAULT_SPEC_REL.as_posix(),
            "box": None,
            "assembly": None,
            "box_overrides": {},
            "note": f"committed example spec rejected: {type(exc).__name__}: {exc}",
        }
    box = _jsonable(dict(spec.cabinet.__dict__)) if hasattr(spec.cabinet, "__dict__") else {}
    assembly = (_jsonable(dict(spec.assembly.__dict__))
                if hasattr(spec.assembly, "__dict__") else {})
    # A search-range spec fixes only the wall thickness concretely; no single W/H/D box exists.
    overrides = {"wall_m": float(spec.cabinet.wall_mm) / 1000.0}
    return {
        "source": DEFAULT_SPEC_REL.as_posix(),
        "experiment_id": spec.experiment_id,
        "box": box,
        "assembly": assembly,
        "box_overrides": overrides,
        "note": ("The committed example spec gives search ranges, not one box; --overrides takes a "
                 "concrete shortlisted box (Boundary Lab's provider default when omitted)."),
    }


def stage_options(root: str | Path, store: str | Path) -> dict[str, Any]:
    """Allow-listed horn meshes + physical groups + stage defaults (read-only, never a user path).

    Only ``<store>/system/ref_case/horn_full/*/mesh.msh`` is inspected.  Every returned ``rel`` is
    store-relative and re-verifies inside that folder before its groups are read.
    """
    repo = _root(root)
    st = Path(store)
    base = _allowed_base(st)
    notes: list[str] = []
    meshes: list[dict[str, Any]] = []
    if base.is_dir():
        for candidate in sorted((Path(st) / HORN_SUBDIR).glob("*/mesh.msh")):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if not resolved.is_file() or base not in resolved.parents:
                notes.append(f"ignored mesh outside the allow-list: {candidate.as_posix()}")
                continue
            if resolved.name != "mesh.msh" or resolved.parent.parent != base:
                continue
            rel = resolved.relative_to(base)
            try:
                groups, triangles = _mesh_summary(resolved)
            except Exception as exc:  # noqa: BLE001 - a broken mesh is visible, never hidden
                groups, triangles = [], None
                notes.append(f"{rel.as_posix()}: unreadable mesh ({type(exc).__name__}: {exc})")
            meshes.append({
                "rel": (HORN_SUBDIR / rel).as_posix(),
                "dir": resolved.parent.name,
                "groups": groups,
                "triangles": triangles,
            })
        if not meshes:
            notes.append(
                "no full-domain horn mesh under "
                f"{_store_label(repo, Path(st) / HORN_SUBDIR)}/*/mesh.msh")
    else:
        notes.append(
            "no full-domain horn mesh folder at "
            f"{_store_label(repo, Path(st) / HORN_SUBDIR)}; stage is unavailable")
    notes.append("meshes are read only from the allow-listed ref_case/horn_full folder; "
                 "groups come from the file, never a user path")
    return {
        "horn_meshes": meshes,
        "default_experiment_id": _default_experiment_id(),
        "defaults": _spec_defaults(repo),
        "clearance_note": (
            f"Horn/box clearance is fixed at the R16 {DEFAULT_MIN_GAP_M * 1000:g} mm minimum; "
            "it is not a stage choice."),
        "notes": notes,
    }


# --------------------------------------------------------------------------- argv builders


def _overrides_arg(value: Any) -> dict[str, float] | None:
    if value in (None, "", {}):
        return None
    if not isinstance(value, Mapping):
        raise StageArgError("overrides: must be a JSON object of vented-source values")
    out: dict[str, float] = {}
    for key, entry in value.items():
        if not isinstance(key, str) or not _OVERRIDE_KEY.fullmatch(key):
            raise StageArgError(f"overrides: invalid vented-source key {key!r}")
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise StageArgError(f"overrides: {key} must be a finite number")
        number = float(entry)
        if not math.isfinite(number):
            raise StageArgError(f"overrides: {key} must be a finite number")
        out[key] = number
    return out


def _spec_arg(root: str | Path, value: Any) -> None:
    """Validate an optional saved spec (it supplies ranges, never one concrete box)."""
    if value in (None, ""):
        return
    if not isinstance(value, str) or not value.strip():
        raise StageArgError("spec: a repo-relative YAML path is required")
    repo = _root(root)
    path = (repo / value.strip()).resolve()
    if (repo.resolve() not in path.parents or path.suffix.lower() not in (".yaml", ".yml")
            or not path.is_file()):
        raise StageArgError(f"spec: not a YAML file inside the repository: {value!r}")
    try:
        C.parse_system_spec_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except Exception as exc:  # noqa: BLE001 - surface the parser's own message
        raise StageArgError(f"spec: {exc}") from None


def stage_argv(root: str | Path, store: str | Path, payload: Mapping[str, Any]) -> list[str]:
    """The ``stage ...`` argv for one validated Boundary Lab staging request.

    ``horn_mesh`` is required and allow-listed; ``source_group`` must be one of that mesh's own 2D
    physical groups; ``translation_z_mm`` is bounded and x/y stay 0; ``experiment_id`` is a safe
    label defaulting to ``bl_gui_<YYYYMMDD>``.  ``backend`` is accepted only as ``beat_cpu`` (and is
    not forwarded: staging is CPU work).  A ``clearance_m`` field is REFUSED: the R16 minimum is a
    fixed 1 mm gate, not a stage argument (senior review 2026-11-20 F5).
    """
    if not isinstance(payload, Mapping):
        raise StageArgError(f"payload must be a mapping, got {type(payload).__name__}")

    backend = payload.get("backend")
    if backend not in (None, "") and str(backend) != "beat_cpu":
        raise StageArgError("backend: only beat_cpu is allowed for GUI system jobs")

    _spec_arg(root, payload.get("spec"))
    overrides = _overrides_arg(payload.get("overrides"))

    mesh_path, mesh_rel = _resolve_horn_mesh(root, store, payload.get("horn_mesh"))
    try:
        groups, _ = _mesh_summary(mesh_path)
    except Exception as exc:  # noqa: BLE001
        raise StageArgError(
            f"horn_mesh: cannot read physical groups ({type(exc).__name__}: {exc})") from None

    group = payload.get("source_group")
    if not isinstance(group, str) or not group.strip():
        raise StageArgError("source_group: a 2D physical group of the horn mesh is required")
    group = group.strip()
    if group not in groups:
        raise StageArgError(
            f"source_group: {group!r} is not a 2D physical group of the horn mesh; "
            f"available: {', '.join(groups) or '(none)'}")

    z = _float_arg(payload.get("translation_z_mm"), TRANSLATION_Z_MIN, TRANSLATION_Z_MAX,
                   "translation_z_mm", 0.0)
    experiment = _key_arg(payload.get("experiment_id"), "experiment_id", _default_experiment_id())

    if payload.get("clearance_m") not in (None, ""):
        raise StageArgError(
            "clearance: fixed at the R16 1 mm minimum; not a stage argument")

    argv = ["stage"]
    if overrides:
        argv += ["--overrides", json.dumps(overrides, sort_keys=True, separators=(",", ":"))]
    argv += [
        "--horn-mesh", _path_label(root, store, mesh_rel.parts),
        "--source-group", group,
        "--translation-mm", "0", "0", format(z, "g"),
        "--experiment-id", experiment,
        "--out", _store_label(root, store),
    ]
    return argv


def stage_preview(root: str | Path, store: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """The validated argv a ``hw-stage`` launch would use (same single validation path)."""
    return {"argv": stage_argv(root, store, payload), "gpu": False}


def validate_argv(root: str | Path, store: str | Path, payload: Mapping[str, Any]) -> list[str]:
    """The ``validate <exp>/<case>`` argv for an existing staged case inside the store."""
    if not isinstance(payload, Mapping):
        raise StageArgError(f"payload must be a mapping, got {type(payload).__name__}")
    _, rel = _resolve_case(root, store, payload.get("case"))
    return ["validate", _path_label(root, store, rel.parts)]


def solve_argv(root: str | Path, store: str | Path, payload: Mapping[str, Any]) -> list[str]:
    """The ``solve ...`` argv, or a refusal naming owner decision 6.

    Gate D is unanswered, so this refuses unless BOTH ``HORNLAB_GUI_ALLOW_BL_SOLVE=1`` and a
    *recorded* owner decision 6 are present.  The refusal path is kept even when the flag is set.
    """
    if not isinstance(payload, Mapping):
        raise StageArgError(f"payload must be a mapping, got {type(payload).__name__}")

    preset = payload.get("preset")
    if preset not in SOLVE_PRESETS:
        raise StageArgError(f"preset: must be one of {list(SOLVE_PRESETS)}")

    _, rel = _resolve_case(root, store, payload.get("case"))

    state = authorization_state(root)
    if not state["allowed"]:
        raise StageArgError(
            "hw-solve refused: " + state["reason"] +
            f"; set {ENV_ALLOW_SOLVE}=1 and record the owner's decision-6 authorization first")

    authorized_by = str(payload.get("authorized_by") or "").strip()
    if not authorized_by:
        raise StageArgError("authorized_by: a recorded decision-6 authorization record is required")
    return ["solve", _path_label(root, store, rel.parts),
            "--preset", str(preset), "--authorized-by", authorized_by]


# --------------------------------------------------------------------------- authorization


def _decision_record(root: str | Path) -> dict[str, Any] | None:
    """The recorded owner decision 6, or ``None`` while it is still open/absent."""
    path = _root(root) / READINESS_REL
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    for decision in data.get("decisions") or []:
        if not isinstance(decision, Mapping):
            continue
        raw_id = decision.get("id")
        if raw_id is None:
            continue
        try:
            if int(raw_id) != DECISION_ID:
                continue
        except (TypeError, ValueError):
            continue
        status = str(decision.get("status") or "").strip().lower()
        recorded = (status not in {"", "open", "unanswered", "pending"}
                    and any(decision.get(k) for k in ("answer", "decision", "authorization",
                                                      "authorized_by", "approved_by")))
        return dict(decision) if recorded else None
    return None


def authorization_state(root: str | Path = ".") -> dict[str, Any]:
    """Whether a GUI-started Boundary Lab solve is authorized (always False until gate D).

    Reads ``HORNLAB_GUI_ALLOW_BL_SOLVE`` *and* the recorded owner decision; the flag alone is not
    enough, so gate D is unanswered -> ``allowed`` is False with a reason that names decision 6.
    """
    env_set = os.environ.get(ENV_ALLOW_SOLVE, "").strip() == "1"
    record = _decision_record(root)
    allowed = bool(env_set and record is not None)
    return {
        "allowed": allowed,
        "reason": DECISION_REASON,
        "env_var": ENV_ALLOW_SOLVE,
        "env_set": env_set,
        "decision_recorded": record is not None,
        "decision_status": None if record is None else record.get("status"),
    }


# --------------------------------------------------------------------------- solve presets


def _recorded_runs(store: str | Path) -> list[dict[str, Any]]:
    base = Path(store) / "system"
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/*/run/manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        freqs = [float(f) for f in (manifest.get("frequencies_hz") or [])]
        elapsed: float | None = None
        try:
            started = _dt.datetime.fromisoformat(str(manifest.get("started_at_utc")))
            finished = _dt.datetime.fromisoformat(str(manifest.get("finished_at_utc")))
            elapsed = (finished - started).total_seconds()
        except (TypeError, ValueError):
            elapsed = None
        rows.append({
            "key": f"{path.parents[2].name}/{path.parents[1].name}",
            "frequencies_hz": freqs,
            "elapsed_s": elapsed,
            "status": manifest.get("status"),
        })
    return rows


def _log_grid(lo: float, hi: float, count: int) -> list[float]:
    if count <= 1:
        return [float(lo)]
    ratio = (float(hi) / float(lo)) ** (1.0 / (count - 1))
    return [round(float(lo) * ratio ** i, 3) for i in range(count)]


def _match_runs(preset: str, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    meta = _PRESET_META[preset]
    band = meta["band_hz"]
    count = meta["recorded_count"]
    out = []
    for run in runs:
        freqs = run["frequencies_hz"]
        if len(freqs) != count or not freqs:
            continue
        if abs(freqs[0] - band[0]) > 0.5 or abs(freqs[-1] - band[1]) > 0.5:
            continue
        out.append(run)
    return out


def _estimate_text(preset: str, runs: list[dict[str, Any]],
                   recorded: list[dict[str, Any]]) -> str:
    times = [r["elapsed_s"] for r in recorded if r["elapsed_s"] is not None]
    if not times:
        return "estimate unavailable (no recorded run for this preset)"
    lo, hi = min(times), max(times)
    keys = ", ".join(r["key"] for r in recorded)
    if hi - lo < 1.0:
        return f"about {lo:.0f} s (recorded run: {keys})"
    return f"about {lo:.0f}-{hi:.0f} s across {len(times)} recorded runs ({keys})"


def solve_presets(root: str | Path = ".", store: str | Path | None = None) -> dict[str, Any]:
    """The three solve presets: frequency lists and CPU estimates from recorded run manifests.

    A preset with no matching recorded run reports ``estimate unavailable`` and a ``None``
    frequency list; no grid or time is invented.  ``lowband12`` names the documented R3 band and
    log spacing but its estimate stays unavailable until an LF run is recorded.
    """
    st = _store(root, store)
    runs = _recorded_runs(st)
    notes = [
        "estimates are computed from recorded run manifest started/finished timestamps; "
        "a preset with no recorded run says 'estimate unavailable' and no number is fabricated",
    ]
    presets: list[dict[str, Any]] = []
    for preset in SOLVE_PRESETS:
        meta = _PRESET_META[preset]
        recorded = _match_runs(preset, runs)
        if recorded:
            freqs = list(recorded[0]["frequencies_hz"])
            source = f"recorded run {recorded[0]['key']}"
        elif preset == "lowband12":
            freqs = _log_grid(meta["band_hz"][0], meta["band_hz"][1], meta["recorded_count"])
            source = "R3 documented band (20-200 Hz, 12 log-spaced); no recorded run"
        else:
            freqs = None
            source = "no recorded run"
        presets.append({
            "id": preset,
            "label": meta["label"],
            "frequencies_hz": freqs,
            "frequency_count": None if freqs is None else len(freqs),
            "band_hz": list(meta["band_hz"]),
            "frequencies_source": source,
            "estimate_text": _estimate_text(preset, runs, recorded),
            "recorded_runs": [r["key"] for r in recorded],
        })
    return {"presets": presets, "notes": notes}


def solve_request(root: str | Path, store: str | Path, preset: str,
                  case_dir: str | Path | None = None) -> dict[str, Any]:
    """A BL headless request overlay for ``preset`` (frequencies from the recorded grid)."""
    preset_row = next((p for p in solve_presets(root, store)["presets"]
                       if p["id"] == preset), None)
    if preset_row is None:
        raise StageArgError(f"preset: must be one of {list(SOLVE_PRESETS)}")
    freqs = preset_row["frequencies_hz"]
    if not freqs:
        raise StageArgError(
            f"preset {preset}: no recorded frequency grid; refusing to invent one")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "frequencies_hz": freqs,
        "excitation_port_ids": list(_REFERENCE_PORTS),
        "include_project_observations": True,
    }
    probes = _recorded_probes(store)
    if probes:
        payload["probes"] = probes
    return payload


def _recorded_probes(store: str | Path) -> list[dict[str, Any]]:
    """Reuse the probes recorded by the reference smoke request, when one is on disk."""
    base = Path(store) / "system"
    if not base.is_dir():
        return []
    for path in sorted(base.glob("*/**/smoke_request.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        probes = data.get("probes")
        if isinstance(probes, list) and probes:
            return [dict(p) for p in probes if isinstance(p, Mapping)]
    return []


def write_solve_request(case_dir: str | Path, preset: str, *, root: str | Path = ".",
                        store: str | Path | None = None) -> Path:
    """Write ``<case>/<preset>_request.json`` with LF endings; never overwrite.

    Called by the job script (never by the server), exactly as the handoff requires.  The target
    case directory must already exist inside the system store.
    """
    case = Path(case_dir)
    if not case.is_dir():
        raise StageArgError(f"case: directory not found: {case}")
    if store is None:
        # case = <store>/system/<experiment>/<case>
        try:
            store = case.resolve().parents[2]
        except IndexError:
            raise StageArgError("case: cannot locate the system store from the case directory") from None
    target = case / f"{preset}_request.json"
    if target.exists():
        raise StageArgError(f"request already exists: {target}")
    payload = solve_request(root, store, preset, case_dir=case)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    return target
