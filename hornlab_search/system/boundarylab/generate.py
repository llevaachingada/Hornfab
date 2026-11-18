"""Drive Boundary Lab's ORIGINAL bundled vented-enclosure generator (its env, not ours).

Phase I seam (parent plan §9): the installed, pinned BL stays untouched; we build a
``GenerationRequest`` against the provider manifest's ``backend`` factory inside a small
runner that is executed BY Boundary Lab's own Python, capture its NDJSON, verify the mesh
artifacts, and record provenance in the isolated system store. No solver is ever started
here; no blab import happens in the HornLab venv.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from hornlab_search.system import provenance
from hornlab_search.system.boundarylab.probe import (
    BL_CAPABILITY_MISSING,
    BLRoot,
    BLCapabilityError,
)

__all__ = [
    "VENTED_PROVIDER_ID",
    "GenerationResult",
    "generate_vented",
    "runner_path",
]

#: The provider id from the installed manifest (verified by probe.py, not guessed).
VENTED_PROVIDER_ID = "blab.vented_enclosure"

#: The vented provider's guaranteed mesh pair (backend.py of the installed copy: interior/exterior).
EXPECTED_VENTED_MESH_IDS: tuple[str, ...] = ("interior", "exterior")

_MAX_LOG_LINES = 240


def runner_path() -> Path:
    """Absolute path of the BL-side runner (executed by Boundary Lab's own Python)."""
    return Path(__file__).with_name("runner_vented.py")


@dataclass(frozen=True)
class GenerationResult:
    """Verified artifacts of one vented-enclosure generation + its provenance."""

    ok: bool
    case_dir: Path
    output_dir: Path | None
    meshes: tuple[dict, ...]
    mesh_info_sha256: str | None
    port_mouth_diameter_m: float | None
    manifest_path: Path | None
    captured_log_tail: tuple[str, ...]
    returncode: int
    detail: Mapping[str, object] = field(default_factory=dict)


def _require_verified(root: BLRoot) -> None:
    if not root.verified:
        raise BLCapabilityError(
            (f"{BL_CAPABILITY_MISSING}: BLRoot at {root.path} is not verified: " + " | ".join(root.missing),))


def _build_source(root: BLRoot, overrides: Mapping[str, float]) -> dict:
    """Merge overrides on top of the provider manifest's own ``default_source``.

    The adapter does NOT reimplement BL's validation: BL's ``parameters.validate`` runs
    inside the backend and is the only authority on units/ranges/clearances. Here we only
    forbid unknown keys and non-numeric values so typos fail early and locally.
    """
    manifest = root.detail.get("provider_manifest", {})
    defaults = manifest.get("default_source")
    if not isinstance(defaults, dict) or not defaults:
        raise BLCapabilityError(
            (f"{BL_CAPABILITY_MISSING}: provider manifest at {root.path} has no usable "
             "default_source; cannot build a validated source dict",))
    source = dict(defaults)
    for key, value in overrides.items():
        if key not in defaults:
            raise ValueError(
                f"unknown vented-source key {key!r}; allowed keys are the provider manifest's "
                f"default_source keys ({', '.join(sorted(defaults))})")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"vented-source key {key!r} must be a number, got {value!r}")
        source[key] = float(value)
    return source


def _execute(argv: Sequence[str], deadline_s: float, cancel_path: Path | None,
             max_lines: int = _MAX_LOG_LINES) -> tuple[int, list[str]]:
    """Run argv (list form; no shell), stream stdout lines, bound both time and memory of the log.

    Returns (returncode, bounded_log_lines). Timeout expiry or the existence of
    ``cancel_path`` terminates the child (and only this child).
    """
    started = time.monotonic()
    lines: list[str] = []
    proc = subprocess.Popen(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            if time.monotonic() - started > deadline_s:
                proc.terminate()
                lines.append(f"[adapter] timeout after {deadline_s:.0f}s; terminated")
                break
            if cancel_path is not None and cancel_path.exists():
                proc.terminate()
                lines.append("[adapter] cancel flag seen; terminated")
                break
        return proc.wait(), lines
    finally:
        if proc.poll() is None:  # stream ended early (crash): ensure the child is gone
            proc.terminate()
            proc.wait()


def _parse_final_json(lines: Sequence[str]) -> dict | None:
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith("{") and '"ok"' in stripped:
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                continue
    return None


def generate_vented(
    root: BLRoot,
    overrides: Mapping[str, float] | None = None,
    *,
    store_root: str | os.PathLike[str] | None = None,
    case_dir: Path | None = None,
    experiment_id: str = "bl_vented_gen",
    case_name: str = "vented",
    mesh_name: str = "vented",
    timeout_s: float = 1800.0,
    cancel_path: Path | None = None,
    run_now: bool = True,
) -> GenerationResult:
    """Generate one vented enclosure with BL's own generator in BL's own environment.

    ``overrides`` keyset must be a subset of the provider manifest's ``default_source`` keys
    (SI values: metres / m2 / dimensionless). Artifacts land in a fresh immutable case dir
    of the isolated system store. ``run_now=False`` returns the would-be spec without
    executing (used by tests and by dry-run inspection).
    """
    _require_verified(root)
    overrides = dict(overrides or {})
    if case_dir is None:
        case_dir = provenance.new_case_dir(experiment_id, store_root=store_root, tag="vented")
    case_dir = Path(case_dir)
    spec = {
        "case_dir": str(case_dir),
        "bl_src": root.provider_dir,
        "backend": root.detail["provider_manifest"]["backend"],
        "provider_id": root.detail["provider_manifest"]["id"],
        "source": _build_source(root, overrides),
        "mesh_name": mesh_name,
        "case_name": case_name,
        "configuration": {"symmetry_config": {"mode": "off"}},
        "runner_version": "v1",
    }
    if not run_now:
        return GenerationResult(ok=False, case_dir=case_dir, output_dir=None, meshes=(),
                                mesh_info_sha256=None, port_mouth_diameter_m=None,
                                manifest_path=None, captured_log_tail=(),
                                returncode=-1, detail={"spec_dry_run": spec})
    spec_path = case_dir / "adapter_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")
    python = root.python_executable
    if not python:
        raise BLCapabilityError((f"{BL_CAPABILITY_MISSING}: verified BLRoot has no python executable",))
    argv = [python, "-I", "-B", str(runner_path()), str(spec_path)]

    code, log_lines = _execute(argv, timeout_s, cancel_path)
    final = _parse_final_json(log_lines)
    ok = code == 0 and final is not None and final.get("ok") is True
    output_dir = Path(final["output_dir"]) if ok and final else None
    meshes = tuple(final["meshes"]) if ok and final else ()
    mesh_info_sha = final.get("mesh_info_sha256") if ok and final else None
    port_mouth = final.get("port_mouth_diameter_m") if ok and final else None
    if ok:
        ids = {str(mesh.get("id")) for mesh in meshes}
        missing_ids = [expected for expected in EXPECTED_VENTED_MESH_IDS if expected not in ids]
        if missing_ids:
            ok = False
            log_lines.append(
                f"[adapter] verification failed: expected mesh ids {EXPECTED_VENTED_MESH_IDS}, "
                f"got {sorted(ids)}")
        for mesh in meshes:
            path = mesh.get("path")
            if not path or not Path(path).is_file() or Path(path).stat().st_size <= 0:
                ok = False
                log_lines.append(f"[adapter] verification failed: mesh artifact missing/empty: {path}")
    detail = {"argv": argv, "spec_sha256": provenance.file_sha256(spec_path), "overrides": overrides}
    manifest_payload = {
        "kind": "boundarylab_vented_generation",
        "bl_root": root.to_dict(),
        "runner": str(runner_path()),
        "spec": spec,
        "detail": detail,
        "result": None if final is None else final,
    }
    manifest_path = provenance.write_manifest(case_dir, manifest_payload)
    return GenerationResult(
        ok=ok, case_dir=case_dir, output_dir=output_dir, meshes=meshes,
        mesh_info_sha256=mesh_info_sha, port_mouth_diameter_m=port_mouth,
        manifest_path=manifest_path, captured_log_tail=tuple(log_lines[-_MAX_LOG_LINES:]),
        returncode=code, detail=detail)
