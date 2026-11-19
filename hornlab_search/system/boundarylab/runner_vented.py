"""BL-side runner: executed BY Boundary Lab's own interpreter (stdlib + blab only).

Contract
--------
``runner_vented.py <spec.json>`` reads one JSON spec, builds BL's public
``GenerationRequest`` against the provider manifest's backend factory, runs
``EnclosureSession.generate`` and prints NDJSON on stdout:

    {"event":"status","message":...}          (generation progress)
    {"ok":true,  "output_dir":..., "meshes":[...], "mesh_info":...}   (final)
    {"ok":false, "error_type":..., "error":..., "traceback_tail":...} (failure)

Exit codes: 0 success, 2 bad spec, 3 generation failure. The HornLab adapter never imports
blab; this file only runs when invoked by BL's python. It writes ONLY under ``case_dir``.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
import traceback
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def main(argv: list[str]) -> int:
    """``argv`` holds ``sys.argv[1:]``: exactly one entry, the spec path."""
    if len(argv) != 1:
        _emit({"ok": False, "error_type": "UsageError", "error": "runner needs exactly one spec path"})
        return 2
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    for key in ("case_dir", "bl_src", "backend", "source", "provider_id", "mesh_name", "case_name"):
        if key not in spec:
            _emit({"ok": False, "error_type": "SpecError", "error": f"spec missing {key!r}"})
            return 2
    case_dir = Path(spec["case_dir"])
    sys.path.insert(0, str(Path(spec["bl_src"])))

    try:
        from blab.generators import base as gen_base  # BL env only
    except ImportError as exc:
        _emit({"ok": False, "error_type": type(exc).__name__,
               "error": f"blab is not importable in this interpreter: {exc}"})
        return 3

    module_path, factory_name = spec["backend"].rsplit(":", 1)
    backend_mod = importlib.import_module(module_path)
    backend = getattr(backend_mod, factory_name)()  # e.g. enclosure.backend:create_backend
    request = gen_base.GenerationRequest(
        provider_id=spec["provider_id"],
        document_id=spec.get("document_id", "hm_search_vented"),
        mesh_name=spec["mesh_name"],
        source=spec["source"],
        run_root=case_dir / "bl_output",
        case_name=spec["case_name"],
        configuration=spec.get("configuration", {"symmetry_config": {"mode": "off"}}),
    )
    session = backend.create_session(request)

    def status(message: str) -> None:
        _emit({"event": "status", "message": str(message)})

    try:
        response = session.generate(status_callback=status)
    except Exception as exc:  # BL ValueError on invalid params, cancelled errors, mesh failures
        _emit({"ok": False, "error_type": type(exc).__name__, "error": str(exc),
               "traceback_tail": "".join(traceback.format_exc()).splitlines()[-12:]})
        return 3

    geometry = response.geometry
    meshes = []
    for mesh in geometry.meshes:
        path = Path(mesh.mesh_path) if mesh.mesh_path is not None else None
        meshes.append({"id": mesh.id, "purpose": mesh.purpose, "path": None if path is None else str(path),
                       "sha256": None if path is None else _sha256_file(path)})
    patch = None
    for attr in ("configuration_patch", "physical_patch", "patch"):
        candidate = getattr(response, attr, None)
        if candidate is not None:
            patch = {"attr": attr, "data": candidate}
            break
    mesh_info = None
    info_path = geometry.output_dir / "mesh_info.json"
    if info_path.is_file():
        mesh_info = json.loads(info_path.read_text(encoding="utf-8"))
        mesh_info_sha = _sha256_file(info_path)
    else:
        mesh_info_sha = None
    _emit({
        "ok": True,
        "output_dir": str(geometry.output_dir),
        "meshes": meshes,
        "mesh_info_sha256": mesh_info_sha,
        "mesh_info": mesh_info,
        "port_mouth_diameter_m": (geometry.provider_metadata or {}).get("port_mouth_diameter_m"),
        "patch_attr": patch["attr"] if patch else None,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
